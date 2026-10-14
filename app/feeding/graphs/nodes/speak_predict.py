"""
预测问答播报节点

业务说明：
Go active-eta / imminent 命中 → 保留模板 clock/remain。
miss 或命中事件 isAppointment → 冷路径：近 7 日算法（或预约约定）+ 语境史 compact + LLM；
预约仅看该事件自身字段（对齐 Go），不按根/子树聚合；
算法结果 Redis 快照 TTL 10min；样本不足/无约定直接降级，禁止编造与查史用时回落。
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.feeding.graphs.nodes.prompts.system import PREDICT_FALLBACK_SYSTEM_PROMPT
from app.feeding.schemas.intent_result import IntentResult, coerce_intent_result
from app.feeding.services.appointment_event import catalog_event_is_appointment
from app.feeding.services.dim_resolve import resolve_time
from app.feeding.services.event_hierarchy import (
    get_descendant_leaves,
    get_root_event_id,
    is_parent_event,
)
from app.feeding.services.predict_algo import (
    PredictToolResult,
    appointment_tool_result,
    filter_records_for_root,
    half_life_days_for_age_months,
    predict_next_for_records,
    prediction_seven_day_unix_bounds,
)
from app.feeding.services.predict_algo_cache import predict_algo_cache
from app.feeding.services.predict_qa import (
    format_predict_answer,
    match_active_expect_end,
    match_imminent_next_at,
    uncertainty_message,
)
from app.shared.constants import TargetType
from app.shared.feeding_history_compact import build_feeding_history_prompt_blocks
from app.shared.graphs.state_patch import state_get
from app.shared.graphs.stream_llm_collect import stream_llm_collect
from app.shared.history_window import parse_day_word_window, shanghai_tz
from app.shared.http_client import http_client
from app.shared.llm_client import llm_model_config_from_mapping

logger = logging.getLogger(__name__)

# 日词 / 近况：需拉语境史给 LLM
_TEMPORAL_HINT = re.compile(
    r"今天|昨天|前天|今晚|昨晚|今早|明早|本周|这周|上周|最近|这两天|近几天|几天"
)
# 规律/综合问：需看史才能答准
_PATTERN_HINT = re.compile(
    r"隔多久|间隔|勤不勤|一般几点|根据记录|看看最近|规律|比上次|和上次|对比"
)


def _needs_context_history(user_text: str) -> bool:
    """
    是否注入语境紧凑史（方案 B）。

    纯「下次何时/还有多久」不拉史；有日词/近况/规律综合线索才拉。
    """
    text = (user_text or "").strip()
    if not text:
        return False
    filled = parse_day_word_window(text)
    if filled and filled[0] and filled[1]:
        return True
    if _TEMPORAL_HINT.search(text):
        return True
    if _PATTERN_HINT.search(text):
        return True
    return False


def _first_event_ids(intent: Dict[str, Any]) -> List[Dict[str, str]]:
    """收集待匹配的事件 id/name（优先 events[]，回落顶层）。"""
    out: List[Dict[str, str]] = []
    for e in intent.get("events") or []:
        if not isinstance(e, dict):
            continue
        eid = str(e.get("event_id") or "").strip()
        if not eid:
            continue
        out.append(
            {
                "event_id": eid,
                "event_name": str(e.get("event_name") or "").strip(),
            }
        )
    if out:
        return out
    eid = str(intent.get("event_id") or "").strip()
    if eid:
        return [
            {
                "event_id": eid,
                "event_name": str(intent.get("event_name") or "").strip(),
            }
        ]
    for raw in intent.get("event_ids") or []:
        s = str(raw or "").strip()
        if s:
            out.append({"event_id": s, "event_name": ""})
    return out


def _guard_no_history_duration(content: str, fallback: str) -> str:
    """防御：降级文案不得带查史完成句特征。"""
    if "上一次" in content and "用时" in content:
        logger.error("预测播报误含查史用时，强制降级")
        return fallback
    return content


async def speak_predict(state: Any) -> Dict[str, Any]:
    """
    双通道预测播报：Go 命中模板；miss/预约走算法+语境史+LLM。
    """
    intent = coerce_intent_result(state_get(state, "intent_result")).to_plain_dict()
    tt = str(intent.get("target_type") or "").lower()
    rs = str(intent.get("read_source") or "").lower()
    if not (
        tt == TargetType.PREDICT.value
        or (tt == TargetType.READ.value and rs == "predict")
    ):
        return {}

    channel = str(intent.get("predict_channel") or "").strip().lower()
    time_answer = str(intent.get("time_answer") or "").strip().lower()
    device_no = state_get(state, "device_no") or ""
    full_events = (
        state_get(state, "event_dictionary_full")
        or state_get(state, "event_dictionary")
        or []
    )
    user_text = (
        state_get(state, "user_input")
        or state_get(state, "text")
        or intent.get("segment_text")
        or ""
    )
    items = _first_event_ids(intent)
    if not items:
        content = uncertainty_message("")
        intent["content"] = content
        return {
            "intent_result": IntentResult.model_validate(intent),
            "response": content,
        }

    head = items[0]
    eid = head["event_id"]
    ename = head["event_name"]
    if not ename:
        for ev in full_events:
            if str(ev.get("event_id") or "") == eid:
                ename = str(ev.get("event_name") or "").strip()
                break

    root_id = get_root_event_id(eid, full_events) or eid
    # 仅命中事件自身 isAppointment（对齐 Go）；不按根/子树聚合
    is_appt = catalog_event_is_appointment(eid, full_events)

    # 预约不走 Go predict Redis；非预约先试 Go 模板热路径
    if (
        not is_appt
        and channel in ("active", "next")
        and time_answer in ("clock", "remain")
    ):
        anchor: Optional[int] = None
        try:
            if channel == "active":
                eta_items = await http_client.get_predict_active_eta(device_no)
                anchor = match_active_expect_end(eid, eta_items, full_events)
            else:
                pending = await http_client.get_predict_imminent_pending(device_no)
                anchor = match_imminent_next_at(eid, pending, full_events)
        except Exception as exc:
            logger.warning(
                "预测拉数失败，转兜底: channel=%s device_no=%s err=%s",
                channel,
                device_no,
                exc,
            )
            anchor = None
        if anchor is not None:
            content = format_predict_answer(
                anchor_unix=anchor,
                time_answer=time_answer,
                predict_channel=channel,
                event_name=ename,
            )
            content = _guard_no_history_duration(content, uncertainty_message(ename))
            intent["content"] = content
            return {
                "intent_result": IntentResult.model_validate(intent),
                "response": content,
            }

    # —— 冷路径 ——
    content = await _cold_path_answer(
        state=state,
        device_no=device_no,
        user_text=str(user_text or ""),
        event_id=eid,
        root_id=root_id,
        event_name=ename,
        full_events=full_events,
        is_appointment=is_appt,
    )
    content = _guard_no_history_duration(content, uncertainty_message(ename))
    intent["content"] = content
    return {
        "intent_result": IntentResult.model_validate(intent),
        "response": content,
    }


async def _cold_path_answer(
    *,
    state: Any,
    device_no: str,
    user_text: str,
    event_id: str,
    root_id: str,
    event_name: str,
    full_events: List[Dict[str, Any]],
    is_appointment: bool,
) -> str:
    """算法/预约 +（按需）语境史 + LLM；样本不足直接降级。"""
    tool = await _resolve_tool_result(
        device_no=device_no,
        event_id=event_id,
        root_id=root_id,
        event_name=event_name,
        full_events=full_events,
        is_appointment=is_appointment,
    )
    if tool.status == "insufficient_samples":
        return tool.message or "数据量太少，无法预测"
    if tool.status == "no_appointment":
        return tool.message or "还没有约定下次时间"

    # B：纯下次何时只灌工具；有日词/近况/规律线索才拉语境史
    history_text = ""
    if _needs_context_history(user_text):
        history_text = await _load_context_history_compact(
            state=state,
            device_no=device_no,
            user_text=user_text,
            root_id=root_id,
            full_events=full_events,
        )
    return await _llm_predict_answer(
        state=state,
        user_text=user_text,
        history_text=history_text,
        tool=tool,
        event_name=event_name,
    )


async def _resolve_tool_result(
    *,
    device_no: str,
    event_id: str,
    root_id: str,
    event_name: str,
    full_events: List[Dict[str, Any]],
    is_appointment: bool,
) -> PredictToolResult:
    """
    快照优先；预约按命中 eventId 读约定；否则近 7 日算法（按根拉史）。
    """
    # 预约缓存键用事件自身 id；间隔算法仍按根
    cache_key = event_id if is_appointment else root_id
    cached = await predict_algo_cache.get_root(device_no, cache_key)
    if cached and str(cached.get("status") or "") == "ok":
        try:
            return PredictToolResult(
                event_id=str(cached.get("event_id") or cache_key),
                event_name=str(cached.get("event_name") or event_name),
                status="ok",
                last_at=cached.get("last_at"),
                next_at=cached.get("next_at"),
                interval_sec=cached.get("interval_sec"),
                confidence=float(cached.get("confidence") or 0),
                expect_kind=cached.get("expect_kind"),
                expect_duration_sec=cached.get("expect_duration_sec"),
                expect_amount=cached.get("expect_amount"),
                expect_unit=cached.get("expect_unit"),
                expect_leaf_title=cached.get("expect_leaf_title"),
                source=str(cached.get("source") or "cache"),
                message=str(cached.get("message") or ""),
            )
        except Exception as exc:
            logger.warning("快照还原失败，重算: %s", exc)

    if is_appointment:
        # Go appointment_next 按事件 id，不用根聚合
        next_at = await http_client.get_appointment_next(device_no, event_id)
        tool = appointment_tool_result(
            event_id=event_id, event_name=event_name, next_at=next_at
        )
        if tool.status == "ok":
            await predict_algo_cache.put_root(
                device_no, event_id, tool.to_prompt_dict()
            )
        return tool

    start_u, end_u = prediction_seven_day_unix_bounds()
    leaf_ids = _leaf_ids_for_root(root_id, full_events)
    try:
        rows = await http_client.get_filtered_history_events(
            device_no,
            event_ids=leaf_ids or [root_id],
            start_time=start_u,
            end_time=end_u,
            limit=500,
        )
    except Exception as exc:
        logger.warning("近 7 日拉史失败: %s", exc)
        rows = []
    scoped = filter_records_for_root(rows or [], root_id, full_events)
    # 月龄：有画像则用；缺省用默认半衰期
    months = await _baby_age_months(device_no)
    half = half_life_days_for_age_months(months)
    tool = predict_next_for_records(
        event_id=root_id,
        event_name=event_name,
        records=scoped,
        catalog=full_events,
        half_life_days=half,
    )
    if tool.status == "ok":
        await predict_algo_cache.put_root(device_no, root_id, tool.to_prompt_dict())
    return tool


def _leaf_ids_for_root(root_id: str, full_events: List[Dict[str, Any]]) -> List[str]:
    """拉史用叶子 id；根本身是叶则返回 [root]。"""
    rid = str(root_id or "").strip()
    if not rid:
        return []
    if not is_parent_event(rid, full_events):
        return [rid]
    leaves = get_descendant_leaves(rid, full_events)
    ids = [str(x.get("event_id") or "").strip() for x in leaves]
    return [x for x in ids if x] or [rid]


async def _baby_age_months(device_no: str) -> Optional[int]:
    """从画像推月龄；失败返回 None。"""
    try:
        profile = await http_client.get_baby_profile(device_no)
        if not isinstance(profile, dict):
            return None
        # 常见字段：months / ageMonths / birthDate
        for key in ("months", "ageMonths", "age_months"):
            if profile.get(key) is not None:
                return int(profile[key])
        birth = profile.get("birthDate") or profile.get("birth_date")
        if birth:
            tz = shanghai_tz()
            from datetime import datetime as dt

            if isinstance(birth, (int, float)):
                bdt = dt.fromtimestamp(float(birth), tz=tz)
            else:
                s = str(birth).strip()[:10]
                bdt = dt.strptime(s, "%Y-%m-%d").replace(tzinfo=tz)
            now = dt.now(tz=tz)
            months = (now.year - bdt.year) * 12 + (now.month - bdt.month)
            if now.day < bdt.day:
                months -= 1
            return max(0, months)
    except Exception as exc:
        logger.debug("画像月龄不可用: %s", exc)
    return None


async def _load_context_history_compact(
    *,
    state: Any,
    device_no: str,
    user_text: str,
    root_id: str,
    full_events: List[Dict[str, Any]],
) -> str:
    """
    语境 TIME（与查史同方法）解窗 → 拉史 → 共享 compact。

    仅在调用方判定需要语境史时调用；窗内无日词时默认近 7 日。
    """
    start_u, end_u = await _resolve_context_window(
        user_text=user_text,
        state=state,
        device_no=device_no,
    )
    leaf_ids = _leaf_ids_for_root(root_id, full_events)
    try:
        rows = await http_client.get_filtered_history_events(
            device_no,
            event_ids=leaf_ids or [root_id],
            start_time=start_u,
            end_time=end_u,
            limit=200,
        )
    except Exception as exc:
        logger.warning("语境史拉失败: %s", exc)
        rows = []
    if not rows:
        return ""
    history_text, _legend = build_feeding_history_prompt_blocks(rows)
    return history_text or ""


async def _resolve_context_window(
    *,
    user_text: str,
    state: Any,
    device_no: str,
) -> Tuple[int, int]:
    """日词 → 飞轮/TIME LLM；否则近 7 日。"""
    text = (user_text or "").strip()
    filled = parse_day_word_window(text) if text else None
    if filled and filled[0] and filled[1]:
        return int(filled[0]), int(filled[1])
    if text and _TEMPORAL_HINT.search(text):
        try:
            st, et, _src = await resolve_time(
                text,
                utterance=text,
                device_no=device_no,
                llm_model=state_get(state, "llm_model") or {},
                reason="predict_fallback_time",
                allow_flywheel=True,
            )
            if st and st > 0:
                end = int(et) if et and int(et) > 0 else int(datetime.now(tz=shanghai_tz()).timestamp())
                return int(st), end
        except Exception as exc:
            logger.warning("预测兜底 TIME 解析失败: %s", exc)
    return prediction_seven_day_unix_bounds()


async def _llm_predict_answer(
    *,
    state: Any,
    user_text: str,
    history_text: str,
    tool: PredictToolResult,
    event_name: str,
) -> str:
    """原话 + 工具 JSON（+ 按需紧凑史）→ LLM 终答。"""
    tool_json = json.dumps(tool.to_prompt_dict(), ensure_ascii=False)
    hist_block = (
        f"紧凑历史：\n{history_text}\n"
        if (history_text or "").strip()
        else "紧凑历史：（未注入，请仅依据工具 JSON 与原话作答）\n"
    )
    user_payload = (
        f"用户原话：{user_text or '（空）'}\n"
        f"事件：{event_name or tool.event_name or tool.event_id}\n"
        f"预测工具JSON：{tool_json}\n"
        f"{hist_block}"
        "请依据以上信息回答用户。"
    )
    cfg = llm_model_config_from_mapping(state_get(state, "llm_model") or {})
    try:
        content = await stream_llm_collect(
            messages=[{"role": "user", "content": user_payload}],
            model_config=cfg,
            system_prompt=PREDICT_FALLBACK_SYSTEM_PROMPT,
            node_name="speak_predict_fallback_llm",
        )
    except Exception as exc:
        logger.warning("预测兜底 LLM 失败: %s", exc)
        # 降级：有 nextAt 时用简单模板，仍禁止查史用时
        if tool.next_at:
            return format_predict_answer(
                anchor_unix=int(tool.next_at),
                time_answer="remain",
                predict_channel="next",
                event_name=event_name or tool.event_name,
            )
        return uncertainty_message(event_name)
    text = (content or "").strip()
    if not text:
        return uncertainty_message(event_name)
    return text

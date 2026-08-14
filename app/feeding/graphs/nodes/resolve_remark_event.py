"""
分类后备注反查节点

业务说明：
由 route_after_classify 在存在「有名无 id」槽位时进入本节点。
字典匹配仍失败的名称当作备注专名，调 Go filter（空 eventIds、近窗、小 limit）
按本设备历史聚合命中事件。唯一命中写入 event_id 与 remark_keyword；
多命中消歧；零命中无法识别。禁止新建事件类型，不把原始行注入 prompt。
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any, Dict, List, Tuple, Union

from app.feeding.schemas.intent_result import IntentResult, coerce_intent_result
from app.feeding.services.clarification import (
    create_remark_disambiguation_pending,
    pending_to_response_fields,
)
from app.feeding.services.event_hierarchy import get_event_by_id, is_parent_event
from app.feeding.services.event_name_match import match_feeding_event
from app.shared.constants import IntentAction, IntentOp, TargetType
from app.shared.graphs.state_patch import state_get
from app.shared.history_window import enum_to_unix
from app.shared.http_client import http_client

logger = logging.getLogger(__name__)

# 备注反查小页上限（规格 limit≤20，实现取 10）
_REMARK_RESOLVE_LIMIT = 10


def _row_event_id(row: Dict[str, Any]) -> str:
    return str(row.get("eventId") or row.get("event_id") or "").strip()


def _aggregate_leaves_by_remark(
    rows: List[Dict[str, Any]],
    full_events: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    按 event_id 聚合备注命中行，只保留字典可解析且非父的叶子。

    出现次数多的排前面，便于消歧展示，但不静默取众数。
    """
    counts: Counter[str] = Counter()
    for row in rows or []:
        eid = _row_event_id(row)
        if eid:
            counts[eid] += 1
    leaves: List[Dict[str, Any]] = []
    for eid, _ in counts.most_common():
        ev = get_event_by_id(eid, full_events)
        if not ev:
            continue
        if is_parent_event(eid, full_events):
            continue
        leaves.append(ev)
    return leaves


def unresolved_event_slots(
    intent: Dict[str, Any],
) -> List[Tuple[Union[str, int], str]]:
    """
    收集顶层与 events[] 中「有名称、无 event_id」的未定槽位。

    路由与反查节点共用此判定：有名无 id 才需要备注反查（字典未命中专名）。

    Returns:
        [( "top" | 子项下标, 名称 ), ...]
    """
    slots: List[Tuple[Union[str, int], str]] = []
    top_name = str(intent.get("event_name") or "").strip()
    top_id = str(intent.get("event_id") or "").strip()
    if top_name and not top_id:
        slots.append(("top", top_name))
    for idx, item in enumerate(intent.get("events") or []):
        if not isinstance(item, dict):
            continue
        name = str(item.get("event_name") or "").strip()
        eid = str(item.get("event_id") or "").strip()
        if name and not eid:
            slots.append((idx, name))
    return slots


def has_unresolved_event_slots(intent: Dict[str, Any]) -> bool:
    """是否存在有名无 id 的槽位（分类后条件边是否进入备注反查）。"""
    return bool(unresolved_event_slots(intent))


def _apply_leaf_to_slot(
    intent: Dict[str, Any],
    slot: Union[str, int],
    leaf: Dict[str, Any],
    remark_keyword: str,
) -> None:
    """把反查到的叶子写回顶层或 events 子项，并带上备注专名。"""
    eid = str(leaf.get("event_id") or "")
    ename = str(leaf.get("event_name") or "")
    if slot == "top":
        intent["event_id"] = eid
        intent["event_name"] = ename
        intent["remark_keyword"] = remark_keyword
        if (intent.get("op") or "").strip().lower() == IntentOp.READ.value:
            ids = [
                str(x)
                for x in (intent.get("event_ids") or [])
                if x not in (None, "")
            ]
            if eid and eid not in ids:
                ids = [eid] + ids
            intent["event_ids"] = ids
        return
    events = list(intent.get("events") or [])
    if isinstance(slot, int) and 0 <= slot < len(events) and isinstance(events[slot], dict):
        events[slot] = dict(events[slot])
        events[slot]["event_id"] = eid
        events[slot]["event_name"] = ename
        intent["events"] = events
        # 顶层尚无备注时补上，便于确认与正式拉史
        if not (intent.get("remark_keyword") or "").strip():
            intent["remark_keyword"] = remark_keyword
        if not (intent.get("event_id") or "").strip():
            intent["event_id"] = eid
            intent["event_name"] = ename


def _unrecognized_response(names: List[str]) -> Dict[str, Any]:
    """零命中：无法识别，禁止建档与落库确认。"""
    shown = "、".join(names) if names else "该名称"
    content = (
        f"无法识别对应的事件「{shown}」。"
        "请使用事件表中的名称，或确认该专名曾作为备注出现在历史记录中。"
    )
    return {
        "intent_result": IntentResult(
            target_type=TargetType.CONVERSATION.value,
            action=IntentAction.REPLY.value,
            op="",
            event_name="",
            event_id="",
            event_ids=[],
            events=[],
            remark_keyword="",
            missing_events=names,
            is_new_event=False,
            content=content,
            need_confirm=False,
            confirm_message="",
        ),
        "need_confirm": False,
        "confirm_message": "",
        "remark_keyword": "",
    }


async def _filter_by_remark(device_no: str, keyword: str) -> List[Dict[str, Any]]:
    """本设备近窗、空 eventIds、小 limit 备注模糊。"""
    start_time, end_time = enum_to_unix("last_30_days")
    return await http_client.get_filtered_history_events(
        device_no=device_no,
        event_ids=None,
        start_time=start_time,
        end_time=end_time,
        limit=_REMARK_RESOLVE_LIMIT,
        remark=keyword,
    )


async def resolve_remark_event(state: Any) -> Dict[str, Any]:
    """
    分类后备注反查：字典未命中名称 → Go 备注模糊 → 定事件或消歧或无法识别。

    主门控在 route_after_classify（有未定槽位才进入本节点）。
    无槽位早退仅为防御（误连边/缓存边界），不作为跳过反查的主路径。
    """
    if state_get(state, "intent_cache_hit"):
        return {}

    intent = coerce_intent_result(state_get(state, "intent_result")).to_plain_dict()
    slots = unresolved_event_slots(intent)
    # 防御性早退：正常应由路由跳过本节点
    if not slots:
        return {}

    device_no = state_get(state, "device_no") or ""
    full_events = (
        state_get(state, "event_dictionary_full")
        or state_get(state, "event_dictionary")
        or []
    )
    user_input = state_get(state, "user_input") or ""
    # llm_model 供消歧 pending；兼容过渡键 model_config
    llm_model = state_get(state, "llm_model") or state_get(state, "model_config") or {}
    conversation_id = state_get(state, "conversation_id") or None

    fail_names: List[str] = []
    # 已处理过的专名，避免同一句重复 HTTP
    resolved_cache: Dict[str, List[Dict[str, Any]]] = {}

    for slot, name in slots:
        # 再做一次字典匹配（含剥前缀），命中则不必打备注
        matched = match_feeding_event(name, full_events)
        if matched:
            # 字典命中（含正在爬→爬练习）：写回 id，不带备注专名
            if slot == "top":
                intent["event_id"] = str(matched.get("event_id") or "")
                intent["event_name"] = str(
                    matched.get("event_name") or intent.get("event_name") or ""
                )
            else:
                events = list(intent.get("events") or [])
                if (
                    isinstance(slot, int)
                    and 0 <= slot < len(events)
                    and isinstance(events[slot], dict)
                ):
                    events[slot] = dict(events[slot])
                    events[slot]["event_id"] = str(matched.get("event_id") or "")
                    events[slot]["event_name"] = str(
                        matched.get("event_name") or events[slot].get("event_name") or ""
                    )
                    intent["events"] = events
            continue

        if name not in resolved_cache:
            try:
                rows = await _filter_by_remark(device_no, name)
            except Exception as exc:
                logger.warning(f"备注反查失败: name={name}, err={exc}")
                rows = []
            resolved_cache[name] = _aggregate_leaves_by_remark(rows or [], full_events)

        leaves = resolved_cache[name]
        if len(leaves) == 1:
            _apply_leaf_to_slot(intent, slot, leaves[0], name)
            logger.info(
                f"备注反查唯一命中: keyword={name}, "
                f"event={leaves[0].get('event_name')}"
            )
            continue

        if len(leaves) > 1:
            # 多命中：消歧，确认前不拉史不落库
            op = (intent.get("op") or "").strip().lower()
            action = intent.get("action") or IntentAction.ONE.value
            pending = create_remark_disambiguation_pending(
                keyword=name,
                leaves=leaves,
                original_utterance=user_input,
                action=action,
                quantity=intent.get("quantity"),
                match_source=str(intent.get("match_source") or ""),
                device_no=device_no,
                model_config=llm_model,
                conversation_id=conversation_id,
                events=intent.get("events") or [],
                op=op,
                start_time=intent.get("start_time") or intent.get("startTime"),
                end_time=intent.get("end_time") or intent.get("endTime"),
            )
            fields = pending_to_response_fields(pending)
            logger.info(
                f"备注反查多命中消歧: keyword={name}, options={len(leaves)}"
            )
            return {
                "intent_result": IntentResult.model_validate(fields),
                "need_confirm": True,
                "confirm_type": fields.get("confirm_type") or "",
                "confirm_message": fields.get("confirm_message") or "",
                "conversation_id": pending.conversation_id,
                "remark_keyword": name,
            }

        # 零命中
        fail_names.append(name)
        logger.info(f"备注反查零命中: keyword={name}")

    if fail_names:
        # 仍有未定名称 → 整句无法识别（含首次记 AD）
        return _unrecognized_response(fail_names)

    intent["is_new_event"] = False
    # 反查成功后若仍有 CRUD，保持分类给出的 need_confirm
    need_confirm = bool(state_get(state, "need_confirm", True))
    target = intent.get("target_type")
    op = (intent.get("op") or "").strip().lower()
    if target in (TargetType.CONVERSATION.value, TargetType.EXIT.value) and not op:
        need_confirm = False
    return {
        "intent_result": IntentResult.model_validate(intent),
        "need_confirm": need_confirm,
        "remark_keyword": intent.get("remark_keyword") or "",
        "confirm_message": intent.get("confirm_message") or "",
    }

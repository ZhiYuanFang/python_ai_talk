"""
护理留意 LLM 生成节点

业务说明：
调用 llm_client.invoke 拿 JSON，解析并规范为 CareAlertItemDto 列表。
失败时返回空 items，不抛到路由（由路由决定是否 500）。
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.care_alert.graphs.nodes.prompts.care_alert_analyze import (
    build_care_alert_system_prompt,
    build_care_alert_user_message,
)
from app.care_alert.graphs.nodes.prompts.history_compact import (
    build_care_alert_history_prompt_blocks,
)
from app.care_alert.schemas.care_alert import CareAlertItemDto, CareAlertReasonDto
from app.shared.graphs.state_patch import state_get
from app.shared.llm_client import llm_client, llm_model_config_from_mapping
from app.shared.llm_json import loads_llm_json

logger = logging.getLogger(__name__)


def _extract_json_object(raw: str) -> Optional[Dict[str, Any]]:
    """
    从 LLM 原文解析顶层 JSON 对象。

    业务逻辑：经共享去围栏/去注释后 loads；list 则包成 items。
    """
    try:
        data = loads_llm_json(raw)
    except (json.JSONDecodeError, ValueError, TypeError):
        logger.warning("护理留意 JSON 解析失败")
        return None
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        return {"items": data}
    return None


def _as_optional_int(value: Any) -> Optional[int]:
    """宽松转 int；失败则 None。"""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _as_optional_float(value: Any) -> Optional[float]:
    """宽松转 float；失败则 None。"""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_reason(raw: Dict[str, Any], *, age_months: Optional[int]) -> Optional[CareAlertReasonDto]:
    """将 LLM reason 规范为 DTO；缺 type 则丢弃。"""
    if not isinstance(raw, dict):
        return None
    type_raw = str(raw.get("type") or "").strip()
    if not type_raw:
        return None
    score = _as_optional_float(raw.get("score"))
    if score is None:
        score = 0.0
    # 夹逼到合理区间，避免离谱分数
    score = max(0.0, min(1.0, score))

    detail_raw = raw.get("detailLines", raw.get("detail_lines"))
    detail_lines: List[str] = []
    if isinstance(detail_raw, list):
        for e in detail_raw:
            s = str(e).strip() if e is not None else ""
            if s:
                detail_lines.append(s)

    age = _as_optional_int(raw.get("ageMonths", raw.get("age_months")))
    if age is None:
        age = age_months

    expectation = raw.get("expectationUsed", raw.get("expectation_used"))
    expectation_used = expectation is True or str(expectation).lower() in ("true", "1")

    still = raw.get("stillExpected", raw.get("still_expected"))
    still_expected: Optional[bool]
    if still is None or still == "":
        still_expected = None
    else:
        still_expected = still is True or str(still).lower() in ("true", "1")

    return CareAlertReasonDto(
        type=type_raw,
        score=score,
        expectation_used=expectation_used,
        age_months=age,
        median_gap_ms=_as_optional_int(raw.get("medianGapMs", raw.get("median_gap_ms"))),
        last_gap_ms=_as_optional_int(raw.get("lastGapMs", raw.get("last_gap_ms"))),
        expect_gap_max_ms=_as_optional_int(
            raw.get("expectGapMaxMs", raw.get("expect_gap_max_ms"))
        ),
        p75_dur_ms=_as_optional_int(raw.get("p75DurMs", raw.get("p75_dur_ms"))),
        elapsed_ms=_as_optional_int(raw.get("elapsedMs", raw.get("elapsed_ms"))),
        expect_dur_max_ms=_as_optional_int(
            raw.get("expectDurMaxMs", raw.get("expect_dur_max_ms"))
        ),
        daily_avg=_as_optional_float(raw.get("dailyAvg", raw.get("daily_avg"))),
        recent_48h_count=_as_optional_int(
            raw.get("recent48hCount", raw.get("recent_48h_count"))
        ),
        still_expected=still_expected,
        detail_lines=detail_lines,
    )


def _default_follow_up(event_name: str, summary_line: str) -> str:
    """缺省追问文案：保证可注入树洞。"""
    name = (event_name or "这条记录").strip()
    summary = (summary_line or "").strip()
    if summary:
        return f"关于「{name}」我想再问问：{summary}，你觉得我需要留意什么吗？"
    return f"关于宝宝的「{name}」最近情况，你觉得有什么值得我留意的吗？"


def _parse_legend_pairs(legend: str) -> List[Tuple[str, str]]:
    """解析「事件名=id」对照表行为 (name, id) 列表。"""
    pairs: List[Tuple[str, str]] = []
    for line in (legend or "").splitlines():
        s = line.strip()
        if not s or "=" not in s:
            continue
        name, eid = s.split("=", 1)
        name, eid = name.strip(), eid.strip()
        if name and eid:
            pairs.append((name, eid))
    return pairs


def _pick_fallback_event(
    history_events: List[Dict[str, Any]],
    legend_pairs: List[Tuple[str, str]],
) -> Optional[Tuple[str, str, int]]:
    """
    启发式挑选兜底事件：近两日出现次数最多的对照表事件；并列取对照表靠前。

    Returns:
        (event_name, event_id, recent_count) 或 None
    """
    if not legend_pairs:
        return None
    # 统计近两日各 name 出现次数（仅对照表内）
    allowed = {n: eid for n, eid in legend_pairs}
    counts: Dict[str, int] = {n: 0 for n in allowed}
    for raw in history_events or []:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("eventName") or raw.get("event_name") or "").strip()
        if name in counts:
            counts[name] += 1
    # 次数降序，同次数按 legend 顺序
    best_name = None
    best_count = -1
    for name, _eid in legend_pairs:
        c = counts.get(name, 0)
        if c > best_count:
            best_count = c
            best_name = name
    if best_name is None:
        best_name, _ = legend_pairs[0]
        best_count = counts.get(best_name, 0)
    return best_name, allowed[best_name], max(0, best_count)


def synthesize_soft_care_alert_item(
    *,
    history_events: List[Dict[str, Any]],
    age_months: Optional[int],
) -> Optional[Dict[str, Any]]:
    """
    有史+legend 时合成一条软提醒（LLM 空列表兜底）。

    业务逻辑：
    - 对照表取合法 eventId
    - 低 score、expectationUsed=false；已知月龄写入 ageMonths，不编造常模数字
    - 文案标明结合近两日记录的温和提醒

    Returns:
        camelCase item dict，或无法合成时 None
    """
    from app.tip.graphs.nodes.derive_baby_age import shanghai_now

    history_text, legend = build_care_alert_history_prompt_blocks(
        history_events, now=shanghai_now()
    )
    if not history_text or history_text.strip() == "（无）":
        return None
    pairs = _parse_legend_pairs(legend)
    picked = _pick_fallback_event(history_events, pairs)
    if not picked:
        return None
    event_name, event_id, recent_count = picked

    summary_line = f"值得留意 · {event_name}：结合近两日记录可多看看"
    detail = "近两日有相关记录，结合月龄做温和提醒（非诊断）"
    if recent_count > 0:
        detail = f"近两日约出现 {recent_count} 次相关记录；{detail}"

    reason = CareAlertReasonDto(
        type="softHistoryReminder",
        score=0.35,
        expectation_used=False,
        age_months=age_months if isinstance(age_months, int) else None,
        recent_48h_count=recent_count if recent_count > 0 else None,
        detail_lines=[detail],
    )
    item = CareAlertItemDto(
        suggestion_id=str(uuid.uuid4()),
        event_id=event_id,
        event_name=event_name,
        summary_line=summary_line,
        follow_up_prompt=_default_follow_up(event_name, summary_line),
        reasons=[reason],
    )
    return item.model_dump(by_alias=True, exclude_none=True)


def ensure_min_one_care_alert_item(
    items: List[Dict[str, Any]],
    *,
    history_events: List[Dict[str, Any]],
    age_months: Optional[int],
) -> List[Dict[str, Any]]:
    """
    有史+legend 且 items 为空时注入一条软兜底。

    Returns:
        原列表或含兜底的单元素列表
    """
    if items:
        return items
    soft = synthesize_soft_care_alert_item(
        history_events=history_events,
        age_months=age_months,
    )
    if soft is None:
        return items
    logger.info(
        "护理留意 LLM 空列表，已合成软兜底: eventId=%s age=%s",
        soft.get("eventId"),
        age_months,
    )
    return [soft]


def normalize_care_alert_items(
    raw_items: Any,
    *,
    age_months: Optional[int],
) -> List[Dict[str, Any]]:
    """
    将 LLM items 规范为可序列化 dict 列表（camelCase）。

    业务逻辑：
    - 缺 eventId 的项丢弃
    - 补 suggestionId（UUID）
    - 缺 followUpPrompt 时用模板补齐
    - reasons 全空时补一条 type=other
    """
    if not isinstance(raw_items, list):
        return []

    out: List[Dict[str, Any]] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        event_id = str(raw.get("eventId") or raw.get("event_id") or "").strip()
        if not event_id:
            continue
        event_name = str(raw.get("eventName") or raw.get("event_name") or "").strip()
        if not event_name:
            event_name = event_id

        reasons_raw = raw.get("reasons")
        reasons: List[CareAlertReasonDto] = []
        if isinstance(reasons_raw, list):
            for r in reasons_raw:
                if isinstance(r, dict):
                    parsed = _normalize_reason(r, age_months=age_months)
                    if parsed is not None:
                        reasons.append(parsed)
        if not reasons:
            reasons.append(
                CareAlertReasonDto(
                    type="other",
                    score=0.5,
                    expectation_used=False,
                    age_months=age_months,
                    detail_lines=["模型未给出结构化原因，仅供参考留意"],
                )
            )

        summary_line = str(
            raw.get("summaryLine") or raw.get("summary_line") or ""
        ).strip()
        if not summary_line:
            labels = "、".join(r.type for r in reasons[:2])
            summary_line = f"值得留意 · {event_name}：{labels}"

        follow_up = str(
            raw.get("followUpPrompt") or raw.get("follow_up_prompt") or ""
        ).strip()
        if not follow_up:
            follow_up = _default_follow_up(event_name, summary_line)

        suggestion_id = str(
            raw.get("suggestionId") or raw.get("suggestion_id") or ""
        ).strip()
        if not suggestion_id:
            suggestion_id = str(uuid.uuid4())

        item = CareAlertItemDto(
            suggestion_id=suggestion_id,
            event_id=event_id,
            event_name=event_name,
            summary_line=summary_line,
            follow_up_prompt=follow_up,
            reasons=reasons,
        )
        out.append(item.model_dump(by_alias=True, exclude_none=True))

    return out


async def generate_care_alerts(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    调用 LLM 生成护理留意 items。

    Args:
        state: 含 day、月龄、历史、画像、llm_model

    Returns:
        {"items": [...]}；有史+legend 时保证至少 1 条（含软兜底）
    """
    model_config = llm_model_config_from_mapping(
        state_get(state, "llm_model") or state_get(state, "model_config")
    )

    baby_age_months: Optional[int] = state_get(state, "baby_age_months")
    age_for_norm = baby_age_months if isinstance(baby_age_months, int) else None
    history_events = state_get(state, "history_events") or []

    # system：本地 prompt 静态块；user：运行时月龄/历史
    system_prompt = build_care_alert_system_prompt()
    user_message = build_care_alert_user_message(
        day=str(state_get(state, "day") or ""),
        baby_age_months=baby_age_months,
        history_events=history_events,
        baby_profile=state_get(state, "baby_profile") or {},
        history_summary=state_get(state, "history_summary"),
    )

    # 无 model 时 model_config 为 None，invoke 将直接失败；日志勿解引用
    logger.info(
        "护理留意 LLM 调用: provider=%s name=%s history=%s",
        model_config.provider if model_config else "(missing)",
        model_config.name if model_config else "-",
        len(history_events),
    )

    resp = await llm_client.invoke(
        messages=[{"role": "user", "content": user_message}],
        model_config=model_config,
        system_prompt=system_prompt,
    )
    raw_text = (resp.content or "").strip()
    data = _extract_json_object(raw_text)
    if data is None:
        logger.warning("护理留意 LLM 输出无法解析为 JSON，尝试软兜底")
        items: List[Dict[str, Any]] = []
    else:
        items = normalize_care_alert_items(
            data.get("items"),
            age_months=age_for_norm,
        )

    # 有史+legend 且仍空 → 确定性软兜底（仍会进入 analyze 快照写入）
    items = ensure_min_one_care_alert_item(
        items,
        history_events=history_events,
        age_months=age_for_norm,
    )
    logger.info("护理留意生成完成: count=%s", len(items))
    return {"items": items}

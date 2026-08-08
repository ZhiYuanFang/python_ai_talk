"""
护理留意 LLM 生成节点

业务说明：
调用 llm_client.invoke 拿 JSON，解析并规范为 CareAlertItemDto 列表。
失败时返回空 items，不抛到路由（由路由决定是否 500）。
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any, Dict, List, Optional

from app.care_alert.graphs.nodes.prompts.care_alert_analyze import (
    build_care_alert_system_prompt,
    build_care_alert_user_message,
)
from app.care_alert.schemas.care_alert import CareAlertItemDto, CareAlertReasonDto
from app.shared.llm_client import LLMModelConfig, llm_client

logger = logging.getLogger(__name__)

# 从夹杂文本中抠 JSON 对象
_JSON_OBJECT_RE = re.compile(r"\{[\s\S]*\}")


def _extract_json_object(raw: str) -> Optional[Dict[str, Any]]:
    """
    从 LLM 原文解析顶层 JSON 对象。

    业务逻辑：
    1. 直接 json.loads
    2. 去掉 ```json 代码块围栏后再 loads
    3. 正则抠第一个大括号对象
    """
    text = (raw or "").strip()
    if not text:
        return None

    # 去掉常见 Markdown 代码围栏
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    for candidate in (text,):
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
            if isinstance(data, list):
                return {"items": data}
        except json.JSONDecodeError:
            pass

    match = _JSON_OBJECT_RE.search(text)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            logger.warning("护理留意 JSON 正则命中但解析失败")
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
        return f"闺蜜，关于「{name}」我想再问问：{summary}，你觉得我需要留意什么吗？"
    return f"闺蜜，关于宝宝的「{name}」最近情况，你觉得有什么值得我留意的吗？"


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
        state: 含 day、月龄、历史、知识、画像、model_config

    Returns:
        {"items": [...]}；解析失败时 items=[]
    """
    model_config_dict = state.get("model_config") or {}
    model_config = LLMModelConfig(**model_config_dict)

    # 月龄：请求透传优先已在 state；未知为 None
    if "baby_age_months" not in state:
        baby_age_months = None
    else:
        baby_age_months = state.get("baby_age_months")

    system_prompt = build_care_alert_system_prompt()
    user_message = build_care_alert_user_message(
        day=str(state.get("day") or ""),
        baby_age_months=baby_age_months,
        history_events=state.get("history_events") or [],
        knowledge_results=state.get("knowledge") or [],
        baby_profile=state.get("baby_profile") or {},
        history_summary=state.get("history_summary"),
    )

    logger.info(
        "护理留意 LLM 调用: provider=%s name=%s history=%s knowledge=%s",
        model_config.provider,
        model_config.name,
        len(state.get("history_events") or []),
        len(state.get("knowledge") or []),
    )

    resp = await llm_client.invoke(
        messages=[{"role": "user", "content": user_message}],
        model_config=model_config,
        system_prompt=system_prompt,
    )
    raw_text = (resp.content or "").strip()
    data = _extract_json_object(raw_text)
    if data is None:
        logger.warning("护理留意 LLM 输出无法解析为 JSON，返回空列表")
        return {"items": []}

    items = normalize_care_alert_items(
        data.get("items"),
        age_months=baby_age_months if isinstance(baby_age_months, int) else None,
    )
    logger.info("护理留意生成完成: count=%s", len(items))
    return {"items": items}

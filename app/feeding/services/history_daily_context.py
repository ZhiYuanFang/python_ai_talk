"""
日汇总非次数问的语境策略

业务说明：
吃了哪些、喝了多少、和昨天比走本地短规则；对不上则模型作答并记规则缺口。
禁止把本地摘要加流水原样交给用户。
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from app.feeding.graphs.nodes.prompts.system import (
    HISTORY_DAILY_CONTEXT_SYSTEM_PROMPT,
    HISTORY_MISSING_EVENT_SYSTEM_PROMPT,
)
from app.feeding.services.rule_gap_store import rule_gap_store
from app.shared.feeding_history_compact import build_feeding_history_prompt_blocks
from app.shared.graphs.stream_llm_collect import stream_llm_collect
from app.shared.llm_client import llm_model_config_from_mapping

logger = logging.getLogger(__name__)

_FOOD_RE = re.compile(r"吃了哪些|吃了什么|吃什么|哪些")
_AMOUNT_RE = re.compile(r"喝了多少|吃了多少")
_COMPARE_RE = re.compile(r"和昨天比|比昨天")


def daily_context_kind(text: str) -> str:
    """
    预设日汇总语境。

    Returns:
        food | amount | compare | 空串（走模型）
    """
    raw = text or ""
    if _COMPARE_RE.search(raw):
        return "compare"
    if _AMOUNT_RE.search(raw):
        return "amount"
    if _FOOD_RE.search(raw):
        return "food"
    return ""


def _remark_of(row: Dict[str, Any]) -> str:
    """历史行备注。"""
    for key in ("remark", "eventRemark"):
        text = str(row.get(key) or "").strip()
        if text:
            return text
    return ""


def _number_of(row: Dict[str, Any]) -> int:
    """历史行数量，缺省 0。"""
    raw = row.get("eventNumber")
    if raw in (None, ""):
        raw = row.get("event_number")
    try:
        return int(raw or 0)
    except (TypeError, ValueError):
        return 0


def format_food_list(rows: List[Dict[str, Any]], event_name: str) -> str:
    """只列食物或备注，不带流水。"""
    seen: List[str] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        remark = _remark_of(row)
        if remark and remark not in seen:
            seen.append(remark)
    label = (event_name or "这段").strip()
    if not seen:
        return f"{label}有记录，但没有写下具体内容"
    shown = "、".join(seen[:8])
    return f"{label}有{shown}"


def format_amount_total(rows: List[Dict[str, Any]], event_name: str) -> str:
    """只报合计数量。"""
    total = 0
    unit = ""
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        total += _number_of(row)
        if not unit:
            unit = str(row.get("unit") or row.get("eventUnit") or "").strip()
    label = (event_name or "这段").strip()
    return f"{label}一共{total}{unit}"


def format_compare_deltas(rows: List[Dict[str, Any]]) -> str:
    """只保留相邻日增减，去掉流水。"""
    text, _legend = build_feeding_history_prompt_blocks(rows)
    body = (text or "").strip()
    if not body or body == "（无）":
        return "没有可比较的记录"
    if body.startswith("【本地摘要】"):
        head = body.split("\n\n", 1)[0]
        head = head.replace("【本地摘要】", "", 1).strip()
        return head or "这两天差不多"
    return "没有可比较的相邻日记录"


def rule_answer_for_kind(
    kind: str,
    rows: List[Dict[str, Any]],
    event_name: str,
) -> str:
    """预设语境的本地短答。"""
    if kind == "food":
        return format_food_list(rows, event_name)
    if kind == "amount":
        return format_amount_total(rows, event_name)
    if kind == "compare":
        return format_compare_deltas(rows)
    return ""


def clamp_twenty(text: str) -> str:
    """回答压到二十个字以内。"""
    s = (text or "").strip().replace("\n", "")
    if len(s) <= 20:
        return s
    return s[:20]


async def llm_daily_uncovered(
    *,
    utterance: str,
    rows: List[Dict[str, Any]],
    device_no: str,
    llm_model: Optional[Dict[str, Any]],
) -> str:
    """
    未覆盖日汇总语境：模型作答并记规则缺口。

    Side Effects:
        写入 history_speak_context 规则缺口。
    """
    compact, _legend = build_feeding_history_prompt_blocks(rows)
    payload = (
        f"用户原话：{(utterance or '').strip()}\n"
        f"紧凑历史：\n{compact or '（无）'}\n"
        "请用口语回答，不要复述整段流水。"
    )
    answer = ""
    try:
        answer = await stream_llm_collect(
            messages=[{"role": "user", "content": payload}],
            model_config=llm_model_config_from_mapping(llm_model or {}),
            system_prompt=HISTORY_DAILY_CONTEXT_SYSTEM_PROMPT,
            node_name="history_daily_context_llm",
        )
    except Exception as exc:
        logger.warning("日汇总语境模型失败: %s", exc)
    text = (answer or "").strip() or "这段记录暂时说不清，请换种问法。"
    try:
        rule_gap_store.record(
            dimension="history_speak_context",
            segment_text=(utterance or "").strip(),
            utterance=(utterance or "").strip(),
            reason="daily_context_uncovered",
            llm_used=True,
            llm_result=text,
            device_no=device_no,
        )
    except Exception as exc:
        logger.warning("日汇总规则缺口写入失败: %s", exc)
    return text


async def llm_missing_event_guess(
    *,
    utterance: str,
    rows: List[Dict[str, Any]],
    device_no: str,
    llm_model: Optional[Dict[str, Any]],
) -> str:
    """
    无事件编号：二十字内猜测，记规则缺口，不写事件飞轮（由调用方保证）。

    Side Effects:
        写入 history_missing_event 规则缺口。
    """
    compact, _legend = build_feeding_history_prompt_blocks(rows)
    payload = (
        f"用户原话：{(utterance or '').strip()}\n"
        f"历史：\n{compact or '（无）'}\n"
        "请在二十个字以内回答，不要追问事件。"
    )
    answer = ""
    try:
        answer = await stream_llm_collect(
            messages=[{"role": "user", "content": payload}],
            model_config=llm_model_config_from_mapping(llm_model or {}),
            system_prompt=HISTORY_MISSING_EVENT_SYSTEM_PROMPT,
            node_name="history_missing_event_llm",
        )
    except Exception as exc:
        logger.warning("无事件猜测模型失败: %s", exc)
    text = clamp_twenty(answer or "") or "这段没有相关记录"
    try:
        rule_gap_store.record(
            dimension="history_missing_event",
            segment_text=(utterance or "").strip(),
            utterance=(utterance or "").strip(),
            reason="missing_event_id",
            llm_used=True,
            llm_result=text,
            device_no=device_no,
        )
    except Exception as exc:
        logger.warning("无事件规则缺口写入失败: %s", exc)
    return text

"""
意图缓存命中后的槽位覆盖节点（已退役）

业务说明：
整包缓存后覆盖已并入段级 TIME/QTY；本节点不再挂接意图主图。
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.feeding.schemas.intent_result import IntentResult, coerce_intent_result
from app.feeding.services.closed_interval import (
    apply_time_slots_to_events,
    should_degrade_multi_clock,
    should_degrade_partial_clock,
)
from app.feeding.services.intent_events import normalize_intent_events
from app.feeding.utils.time_slot_extractor import extract_clocks_from_text
from app.shared.graphs.state_patch import state_get

logger = logging.getLogger(__name__)


def overlay_slots(state: Any) -> Dict[str, Any]:
    """
    缓存命中后覆盖时间与数量；必要时降级。

    Returns:
        更新后的 intent_result；或 intent_cache_hit=False 以触发分类
    """
    if not state_get(state, "intent_cache_hit"):
        return {}
    text = state_get(state, "user_input") or state_get(state, "text") or ""
    intent = coerce_intent_result(state_get(state, "intent_result")).to_plain_dict()
    intent = normalize_intent_events(intent)
    events = [e for e in (intent.get("events") or []) if isinstance(e, dict)]
    if not events:
        return {}

    clocks = extract_clocks_from_text(text)
    # 多钟点 OR 半命中 → 取消免确认，走分类
    multi = should_degrade_multi_clock(text, clocks, events)
    partial = should_degrade_partial_clock(text, clocks)
    if multi or partial:
        logger.info(
            "槽位覆盖降级: clocks=%s multi=%s partial=%s，取消缓存免确认",
            len(clocks),
            multi,
            partial,
        )
        return {
            "intent_cache_hit": False,
            "need_confirm": True,
            "matched_vector_id": None,
        }

    new_events, changed = apply_time_slots_to_events(text, events)
    if not changed:
        logger.info("槽位覆盖无变更: clocks=%s", len(clocks))
        return {}

    intent["events"] = new_events
    if new_events and new_events[0].get("quantity") is not None:
        intent["quantity"] = new_events[0].get("quantity")
    logger.info(
        "槽位覆盖完成: clocks=%s events=%s",
        len(clocks),
        len(new_events),
    )
    return {
        "intent_result": IntentResult.model_validate(intent),
        "intent_cache_hit": True,
        "need_confirm": False,
    }

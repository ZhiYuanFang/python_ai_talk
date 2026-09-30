"""
意图缓存命中后的槽位覆盖节点

业务说明：
从本轮原文用规则抽取 clock / quantity，盖到缓存 events[] 后再免确认执行。
多钟点且 events 仅一条时取消命中，降级走分类 LLM。
不修改 op / event_id / action 骨架。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.feeding.schemas.intent_result import IntentResult, coerce_intent_result
from app.feeding.services.intent_events import normalize_intent_events
from app.feeding.utils.quantity_extractor import extract_quantities_from_text
from app.feeding.utils.time_slot_extractor import extract_clocks_from_text
from app.shared.constants import IntentOp
from app.shared.graphs.state_patch import state_get

logger = logging.getLogger(__name__)


def overlay_slots(state: Any) -> Dict[str, Any]:
    """
    缓存命中后覆盖钟点与数量；必要时降级。

    Returns:
        更新后的 intent_result；或 intent_cache_hit=False 以触发分类
    """
    if not state_get(state, "intent_cache_hit"):
        return {}
    text = state_get(state, "user_input") or state_get(state, "text") or ""
    intent = coerce_intent_result(state_get(state, "intent_result")).to_plain_dict()
    intent = normalize_intent_events(intent)
    events: List[Dict[str, Any]] = [
        dict(e) for e in (intent.get("events") or []) if isinstance(e, dict)
    ]
    if not events:
        return {}

    clocks = extract_clocks_from_text(text)
    qtys = extract_quantities_from_text(text)

    # 多钟点对单条：强制降级 LLM
    if len(clocks) >= 2 and len(events) == 1:
        logger.info(
            "槽位覆盖降级: clocks=%s events=1，取消缓存免确认",
            len(clocks),
        )
        return {
            "intent_cache_hit": False,
            "need_confirm": True,
            "matched_vector_id": None,
        }

    changed = False
    # 按顺序 zip 覆盖（条数对齐时逐条；单条时盖第一条）
    n = len(events)
    for i, ev in enumerate(events):
        op = str(ev.get("op") or "").strip().lower()
        if clocks:
            if n == 1 and len(clocks) == 1:
                ev["start_time"] = clocks[0].unix
                if op == IntentOp.CREATE.value:
                    # 瞬时 create：end 与 start 对齐；计时 start 仍 end=0 由 collect 处理
                    action = str(ev.get("action") or "").strip().lower()
                    if action != "start":
                        ev["end_time"] = clocks[0].unix
                changed = True
            elif i < len(clocks):
                ev["start_time"] = clocks[i].unix
                if op == IntentOp.CREATE.value:
                    action = str(ev.get("action") or "").strip().lower()
                    if action != "start":
                        ev["end_time"] = clocks[i].unix
                changed = True
        if qtys:
            if n == 1 and qtys:
                ev["quantity"] = qtys[0]
                changed = True
            elif i < len(qtys):
                ev["quantity"] = qtys[i]
                changed = True

    if not changed:
        logger.info("槽位覆盖无变更: clocks=%s qtys=%s", len(clocks), len(qtys))
        return {}

    intent["events"] = events
    # 顶层 quantity 与首条对齐，便于旧路径读取
    if events and events[0].get("quantity") is not None:
        intent["quantity"] = events[0].get("quantity")
    logger.info(
        "槽位覆盖完成: clocks=%s qtys=%s events=%s",
        len(clocks),
        len(qtys),
        len(events),
    )
    return {
        "intent_result": IntentResult.model_validate(intent),
        "intent_cache_hit": True,
        "need_confirm": False,
    }

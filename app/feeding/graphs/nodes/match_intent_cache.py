"""
意图缓存匹配节点

业务说明：
相似度与质量分双门槛命中则采用缓存的 op + events，跳过分类 LLM。
同一设备短窗内对刚免确认执行过的同一问：扣分并当未命中。
改/删不带 history_id，由后续执行层现查。
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.feeding.services.intent_cache_store import (
    INTENT_CACHE_HIGH_THRESHOLD,
    INTENT_CACHE_QUALITY_MIN,
    intent_cache_store,
    last_cache_turn_store,
)
from app.feeding.utils.query_utterance import looks_like_history_query
from app.shared.constants import IntentOp, MatchSource

logger = logging.getLogger(__name__)


def match_intent_cache(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    检索意图缓存。

    命中高置信且质量分达标：写入 intent_result，match_source=cache。
    未命中：保持空，交给后续探针/分类。
    """
    text = state.get("user_input") or state.get("text", "")
    device_no = state.get("device_no") or ""
    hits = intent_cache_store.search(text, n_results=1)
    if not hits:
        logger.info("意图缓存未命中")
        return {"intent_cache_hit": False}
    top = hits[0]
    score = float(top.get("score") or 0)
    quality = float(top.get("quality_score") or 0)
    payload = top.get("payload") or {}
    vector_id = str(top.get("id") or "")
    if score < INTENT_CACHE_HIGH_THRESHOLD or not payload.get("op"):
        logger.info(f"意图缓存分数不足: score={score}")
        return {"intent_cache_hit": False, "match_confidence": score}
    if quality < INTENT_CACHE_QUALITY_MIN:
        logger.info(
            f"意图缓存质量分不足: quality={quality}, min={INTENT_CACHE_QUALITY_MIN}"
        )
        return {"intent_cache_hit": False, "match_confidence": score}
    # 短窗内同一问刚免确认执行过：视为否决，扣分后走分类
    repeat_id = last_cache_turn_store.repeat_vector_id(device_no, text)
    if repeat_id and vector_id and repeat_id == vector_id:
        logger.info("短窗重复同一问，意图缓存扣分并当未命中")
        intent_cache_store.penalize(vector_id)
        return {"intent_cache_hit": False, "match_confidence": score}
    # 查询句若缓存成了 create，仍交给分类，避免误记
    if looks_like_history_query(text) and payload.get("op") == IntentOp.CREATE.value:
        logger.info("查询句命中 create 缓存，忽略")
        return {"intent_cache_hit": False}
    intent_result = dict(payload)
    intent_result["match_source"] = "cache"
    intent_result["match_confidence"] = score
    logger.info(
        f"意图缓存命中: op={intent_result.get('op')}, score={score}, "
        f"quality={quality}, events={len(intent_result.get('events') or [])}"
    )
    return {
        "intent_result": intent_result,
        "intent_cache_hit": True,
        "match_confidence": score,
        "match_source": MatchSource.VECTOR.value,
        "need_confirm": False,
        "matched_vector_id": vector_id,
    }

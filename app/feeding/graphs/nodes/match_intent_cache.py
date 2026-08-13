"""
意图缓存匹配节点

业务说明：
高相似命中则采用缓存的 op + events，跳过分类 LLM。
改/删不带 history_id，由后续执行层现查。
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.feeding.services.intent_cache_store import (
    INTENT_CACHE_HIGH_THRESHOLD,
    intent_cache_store,
)
from app.feeding.utils.query_utterance import looks_like_history_query
from app.shared.constants import IntentOp, MatchSource

logger = logging.getLogger(__name__)


def match_intent_cache(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    检索意图缓存。

    命中高置信：写入 intent_result，match_source=cache。
    未命中：保持空，交给后续探针/分类。
    """
    text = state.get("user_input") or state.get("text", "")
    hits = intent_cache_store.search(text, n_results=1)
    if not hits:
        logger.info("意图缓存未命中")
        return {"intent_cache_hit": False}
    top = hits[0]
    score = float(top.get("score") or 0)
    payload = top.get("payload") or {}
    if score < INTENT_CACHE_HIGH_THRESHOLD or not payload.get("op"):
        logger.info(f"意图缓存分数不足: score={score}")
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
        f"events={len(intent_result.get('events') or [])}"
    )
    return {
        "intent_result": intent_result,
        "intent_cache_hit": True,
        "match_confidence": score,
        "match_source": MatchSource.VECTOR.value,
        "need_confirm": False,
    }

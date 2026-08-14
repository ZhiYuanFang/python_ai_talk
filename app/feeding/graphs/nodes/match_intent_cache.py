"""
意图缓存匹配节点

业务说明：
相似度与质量分双门槛命中则采用缓存的 events（含 op），跳过分类 LLM。
旧载荷仅有顶层 op 时投影为 events；无法投影则当未命中。
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.feeding.schemas.intent_result import IntentResult
from app.feeding.services.intent_cache_store import (
    INTENT_CACHE_HIGH_THRESHOLD,
    INTENT_CACHE_QUALITY_MIN,
    intent_cache_store,
    last_cache_turn_store,
)
from app.feeding.services.intent_events import (
    event_ops,
    normalize_intent_events,
)
from app.shared.constants import MatchSource
from app.shared.graphs.state_patch import state_get

logger = logging.getLogger(__name__)


def match_intent_cache(state: Any) -> Dict[str, Any]:
    """
    检索意图缓存。

    命中高置信且质量分达标：写入 intent_result，match_source=cache。
    """
    text = state_get(state, "user_input") or state_get(state, "text", "")
    device_no = state_get(state, "device_no") or ""
    hits = intent_cache_store.search(text, n_results=1)
    if not hits:
        logger.info("意图缓存未命中")
        return {"intent_cache_hit": False}
    top = hits[0]
    score = float(top.get("score") or 0)
    quality = float(top.get("quality_score") or 0)
    payload = top.get("payload") or {}
    vector_id = str(top.get("id") or "")
    if score < INTENT_CACHE_HIGH_THRESHOLD:
        logger.info(f"意图缓存分数不足: score={score}")
        return {"intent_cache_hit": False, "match_confidence": score}
    if quality < INTENT_CACHE_QUALITY_MIN:
        logger.info(
            f"意图缓存质量分不足: quality={quality}, min={INTENT_CACHE_QUALITY_MIN}"
        )
        return {"intent_cache_hit": False, "match_confidence": score}

    # 投影旧顶层 op；无可用 events 则未命中
    normalized = normalize_intent_events(dict(payload))
    if not event_ops(normalized):
        logger.info("意图缓存载荷无可用 events[].op，当未命中")
        return {"intent_cache_hit": False, "match_confidence": score}

    repeat_id = last_cache_turn_store.repeat_vector_id(device_no, text)
    if repeat_id and vector_id and repeat_id == vector_id:
        logger.info("短窗重复同一问，意图缓存扣分并当未命中")
        intent_cache_store.penalize(vector_id)
        return {"intent_cache_hit": False, "match_confidence": score}

    intent_result = normalized
    intent_result["match_source"] = "cache"
    intent_result["match_confidence"] = score
    logger.info(
        "意图缓存命中: ops=%s, score=%s, quality=%s, events=%s",
        list(event_ops(intent_result)),
        score,
        quality,
        len(intent_result.get("events") or []),
    )
    return {
        "intent_result": IntentResult.model_validate(intent_result),
        "intent_cache_hit": True,
        "match_confidence": score,
        "match_source": MatchSource.VECTOR.value,
        "need_confirm": False,
        "matched_vector_id": vector_id,
    }

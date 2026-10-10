"""
意图缓存匹配节点（已退役）

业务说明：
整包意图免确认路径已由 resolve_segments 段多维替代；本模块不再挂接意图主图。
保留文件以免外部误 import 立刻炸；请勿再接入 START。
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.feeding.schemas.intent_result import IntentResult
from app.feeding.services.history_mode_cues import (
    history_mode_cache_conflict,
    infer_expected_history_mode,
    payload_history_mode,
)
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

    # 查史：原文几次 vs 载荷上一次等 mode 冲突 → 拒命中，走分类
    if history_mode_cache_conflict(text, normalized):
        logger.info(
            "意图缓存查史 mode 门闩拒命中: expected=%s, payload_mode=%s, text=%s",
            infer_expected_history_mode(text),
            payload_history_mode(normalized),
            (text or "")[:40],
        )
        return {"intent_cache_hit": False, "match_confidence": score}

    repeat_id = last_cache_turn_store.repeat_vector_id(device_no, text)
    if repeat_id and vector_id and repeat_id == vector_id:
        logger.info("短窗重复同一问，意图缓存扣分并当未命中")
        intent_cache_store.penalize(vector_id)
        return {"intent_cache_hit": False, "match_confidence": score}

    intent_result = normalized
    intent_result["match_source"] = "cache"
    intent_result["match_confidence"] = score
    # 对照用户原话与库内 document，便于排查误匹配、针对性灌种/扣分
    doc = str(top.get("document") or "")
    logger.info(
        "意图缓存命中: query=%s, document=%s, score=%s, quality=%s, id=%s, ops=%s, events=%s",
        (text or "")[:80],
        doc[:80],
        score,
        quality,
        vector_id,
        list(event_ops(intent_result)),
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

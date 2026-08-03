"""Q&A 捷径检索与命中判定节点。"""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.shared.baby_age import age_band_from_months
from app.shared.qa_fast_path import evaluate_qa_hit, is_block_fast_path
from app.shared.vector_store import vector_store

logger = logging.getLogger(__name__)


async def search_qa_fast_path(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    检索全局 Q&A；命中则写 qa_hit/qa_answer，否则 miss。
    """
    months = state.get("baby_age_months")
    age_band = age_band_from_months(months if months is not None else None)
    standalone = (state.get("standalone_question") or "").strip()

    base = {
        "age_band": age_band,
        "qa_hit": False,
        "qa_answer": "",
        "qa_miss_reason": "",
    }

    blocked, reason = is_block_fast_path(state)
    if blocked:
        logger.info("Q&A 检索跳过: reason=%s", reason)
        return {**base, "qa_miss_reason": reason}

    if not standalone:
        reason = state.get("qa_rewrite_miss_reason") or "no_standalone_question"
        logger.info("Q&A 检索跳过: reason=%s", reason)
        return {**base, "qa_miss_reason": str(reason)}

    if not age_band:
        logger.info("Q&A 检索跳过: unknown_age months=%s", months)
        return {**base, "qa_miss_reason": "unknown_age"}

    try:
        candidates = vector_store.search_qa(standalone, n_results=5)
    except Exception as e:
        logger.error("Q&A 检索异常: %s", e, exc_info=True)
        return {**base, "qa_miss_reason": "search_error"}

    hit, miss_reason = evaluate_qa_hit(candidates, age_band=age_band)
    if not hit:
        return {**base, "qa_miss_reason": miss_reason}

    return {
        **base,
        "qa_hit": True,
        "qa_answer": hit["answer"],
        "qa_miss_reason": "",
        "qa_match_id": hit.get("id"),
        "qa_match_score": hit.get("score"),
    }

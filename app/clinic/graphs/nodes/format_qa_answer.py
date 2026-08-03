"""Q&A 命中后的轻量格式化（不重跑完整 clinic_answer）。"""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


async def format_qa_answer(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    命中捷径时确认答案可用；保留库中口语答案，不做二次 LLM。
    """
    answer = str(state.get("qa_answer") or "").strip()
    if not answer:
        logger.warning("format_qa_answer: qa_hit 但答案为空，降级为 miss")
        return {"qa_hit": False, "qa_miss_reason": "empty_qa_answer", "qa_answer": ""}
    logger.info(
        "Q&A 捷径直接回答: id=%s, sim=%s, chars=%s",
        state.get("qa_match_id"),
        state.get("qa_match_score"),
        len(answer),
    )
    return {"qa_answer": answer, "qa_hit": True}

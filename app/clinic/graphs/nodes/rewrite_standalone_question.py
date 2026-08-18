"""改写独立问句节点。"""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.shared.graphs.state_patch import state_get
from app.shared.qa_fast_path import is_block_fast_path, rewrite_standalone_question

logger = logging.getLogger(__name__)


async def rewrite_standalone_question_node(state: Any) -> Dict[str, Any]:
    """
    写出 standalone_question；拦截或失败时置 None（后续 search 必 miss）。

    Args:
        state: 图 State（Pydantic 或 dict）；字段经 state_get 读取。
    """
    blocked, reason = is_block_fast_path(state)
    if blocked:
        logger.info("问句改写跳过（强制 miss）: reason=%s", reason)
        return {
            "standalone_question": None,
            "qa_rewrite_miss_reason": reason,
        }

    text = await rewrite_standalone_question(
        question=str(state_get(state, "question") or ""),
        chat_context=str(state_get(state, "chat_context") or ""),
        model_config=dict(
            state_get(state, "llm_model") or state_get(state, "model_config") or {}
        ),
    )
    if not text:
        return {
            "standalone_question": None,
            "qa_rewrite_miss_reason": "rewrite_failed",
        }
    return {
        "standalone_question": text,
        "qa_rewrite_miss_reason": "",
    }

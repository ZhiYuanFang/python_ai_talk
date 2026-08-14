"""
陪伴同步回答生成

业务说明：
与 stream_response 使用同一套 clinic_answer 提示词，改为 llm_client.invoke 拿全文。
供 POST /v1/clinic 非流式同步生成；clinic HTTP 流式仍走 stream_response。

设计思路：
1. 从 state 读取 question、chat_context、history、knowledge、baby_profile、llm_model
2. 拼装 system/user 消息
3. invoke 返回 {"response": "..."}
"""

import logging
from typing import Any, Dict

from app.clinic.graphs.nodes.prompts.clinic_answer import (
    build_clinic_answer_system_prompt,
    build_clinic_answer_user_message,
    resolve_clinic_needs_history,
)
from app.shared.graphs.state_patch import state_get
from app.shared.llm_client import llm_client, llm_model_config_from_mapping

logger = logging.getLogger(__name__)


async def generate_clinic_answer(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    同步回答：clinic_answer + invoke。

    Args:
        state: 含 question（或 user_input）、chat_context、数据准备结果、llm_model

    Returns:
        {"response": 全文}；失败抛异常由调用方兜底
    """
    question = state_get(state, "question") or state_get(state, "user_input") or ""
    history_events = state_get(state, "history_events", [])
    knowledge = state_get(state, "knowledge", [])
    baby_profile = state_get(state, "baby_profile", {})
    chat_context = state_get(state, "chat_context") or ""
    baby_age_months = state_get(state, "baby_age_months")
    needs_history = resolve_clinic_needs_history(state)

    model_config = llm_model_config_from_mapping(
        state_get(state, "llm_model") or state_get(state, "model_config")
    )
    system_prompt = build_clinic_answer_system_prompt(needs_history=needs_history)
    user_message = build_clinic_answer_user_message(
        question=question,
        history_events=history_events,
        knowledge_results=knowledge,
        baby_profile=baby_profile,
        chat_context=chat_context,
        baby_age_months=baby_age_months,
        needs_history=needs_history,
    )

    resp = await llm_client.invoke(
        messages=[{"role": "user", "content": user_message}],
        model_config=model_config,
        system_prompt=system_prompt,
    )
    text = (resp.content or "").strip()
    if not text:
        logger.warning("同步生成返回空内容")
    return {"response": text}

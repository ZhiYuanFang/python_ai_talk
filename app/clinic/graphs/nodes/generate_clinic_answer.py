"""
闺蜜陪伴同步回答生成

业务说明：
与 stream_response 使用同一套 clinic_answer 提示词，改为 llm_client.invoke 拿全文。
供 intent 的 call_clinic_agent 使用（非 SSE）；clinic HTTP 流式仍走 stream_response。

设计思路：
1. 从 state 读取 question、chat_context、history、knowledge、baby_profile、model_config
2. 拼装闺蜜 system/user 消息
3. invoke 返回 {"response": "..."}
"""

import logging
from typing import Any, Dict

from app.clinic.graphs.nodes.prompts.clinic_answer import (
    build_clinic_answer_system_prompt,
    build_clinic_answer_user_message,
    resolve_clinic_needs_history,
)
from app.shared.llm_client import LLMModelConfig, llm_client

logger = logging.getLogger(__name__)


async def generate_clinic_answer(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    同步闺蜜回答：clinic_answer + invoke。

    Args:
        state: 含 question（或 user_input）、chat_context、数据准备结果、model_config

    Returns:
        {"response": 全文}；失败抛异常由调用方兜底
    """
    question = state.get("question") or state.get("user_input") or ""
    history_events = state.get("history_events", [])
    knowledge = state.get("knowledge", [])
    baby_profile = state.get("baby_profile", {})
    model_config_dict = state.get("model_config", {})
    chat_context = state.get("chat_context") or ""
    baby_age_months = state.get("baby_age_months")
    needs_history = resolve_clinic_needs_history(state)

    model_config = LLMModelConfig(**model_config_dict)
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
        logger.warning("闺蜜同步生成返回空内容")
    return {"response": text}

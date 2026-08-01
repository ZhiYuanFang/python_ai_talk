"""
同步回答生成节点（仅 history 短链）

业务说明：
Intent 图在 history 分支：judge → fetch_history → 本节点。
suggest / conversation 已走 call_clinic_agent + clinic_answer，不再经此节点。

设计思路：
1. 读取 user_input、history_events、model_config
2. 使用 history_answer 提示词调用 LLM
3. 失败时返回错误提示
"""

import logging
from typing import Any, Dict

from app.clinic.graphs.nodes.prompts.history_answer import (
    build_history_answer_system_prompt,
    build_history_answer_user_message,
)
from app.shared.llm_client import LLMModelConfig, llm_client

logger = logging.getLogger(__name__)


async def generate_response(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    History 同步回答生成。

    Args:
        state: 含 user_input、history_events、model_config

    Returns:
        {"response": "..."}
    """
    user_input = state.get("user_input", "")
    history_events = state.get("history_events", [])
    model_config_dict = state.get("model_config", {})
    model_config = LLMModelConfig(**model_config_dict)

    try:
        system_prompt = build_history_answer_system_prompt()
        user_message = build_history_answer_user_message(
            user_text=user_input,
            history_events=history_events,
        )
        response = await llm_client.invoke(
            messages=[{"role": "user", "content": user_message}],
            model_config=model_config,
            system_prompt=system_prompt,
        )
        return {"response": response.content}

    except Exception as e:
        logger.error(f"回答生成 LLM 调用失败: {str(e)}")
        return {"response": "抱歉，生成回答时出现错误，请稍后再试。"}

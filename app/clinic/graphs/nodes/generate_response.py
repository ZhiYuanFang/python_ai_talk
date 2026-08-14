"""
同步回答生成节点（仅 history 短链）

业务说明：
陪伴图内的同步答题节点；意图查记录已改走模板，不再经本节点。

设计思路：
1. 读取 user_input、history_events、llm_model
2. 使用 history_answer 提示词调用 LLM
3. 失败时返回错误提示
"""

import logging
from typing import Any, Dict

from app.clinic.graphs.nodes.prompts.history_answer import (
    build_history_answer_system_prompt,
    build_history_answer_user_message,
)
from app.shared.graphs.state_patch import state_get
from app.shared.constants import LLM_OVERLOAD_RETRY_MESSAGE
from app.shared.llm_client import llm_client, llm_model_config_from_mapping

logger = logging.getLogger(__name__)


async def generate_response(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    History 同步回答生成。

    Args:
        state: 含 user_input、history_events、llm_model

    Returns:
        {"response": "..."}
    """
    user_input = state_get(state, "user_input", "")
    history_events = state_get(state, "history_events", [])
    model_config = llm_model_config_from_mapping(
        state_get(state, "llm_model") or state_get(state, "model_config")
    )

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
        return {"response": LLM_OVERLOAD_RETRY_MESSAGE}

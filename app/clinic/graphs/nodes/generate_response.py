"""
同步回答生成节点

业务说明：
LangGraph 节点：根据意图类型调用 LLM 生成同步回答。
支持 history（历史查询）和 suggest（成长建议）两种意图类型。
使用不同的提示词构建函数和上下文信息。

设计思路：
1. 从 State 中读取 intent_result、history_events、knowledge、baby_profile、model_config
2. 根据 target_type 选择对应的提示词构建函数
3. 调用 LLM 生成回答
4. LLM 失败时返回错误提示
5. 返回 response 更新 State
"""

import logging
from typing import Any, Dict

from app.clinic.graphs.nodes.prompts.history_answer import build_history_answer_system_prompt, build_history_answer_user_message
from app.clinic.graphs.nodes.prompts.suggest_answer import build_suggest_answer_system_prompt, build_suggest_answer_user_message
from app.shared.llm_client import LLMModelConfig, llm_client

# 初始化日志记录器
logger = logging.getLogger(__name__)


async def generate_response(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    同步回答生成节点函数

    业务逻辑：
    1. 从 State 中读取意图类型、历史记录、知识、宝宝画像、模型配置
    2. 根据 target_type 选择对应的系统提示词和用户消息
    3. 调用 LLM 生成回答
    4. LLM 失败时返回错误提示文案
    5. 返回 response 更新 State

    Args:
        state: 当前图状态

    Returns:
        需要更新的 State 字段字典
    """
    # 读取输入参数
    intent_result = state.get("intent_result", {})
    target_type = intent_result.get("target_type", "history")
    user_input = state.get("user_input", "")
    history_events = state.get("history_events", [])
    knowledge = state.get("knowledge", [])
    baby_profile = state.get("baby_profile", {})
    model_config_dict = state.get("model_config", {})

    # 构建模型配置对象
    model_config = LLMModelConfig(**model_config_dict)

    try:
        # 根据意图类型选择提示词
        if target_type == "suggest":
            # 建议意图：使用建议提示词，包含历史、知识、宝宝画像
            system_prompt = build_suggest_answer_system_prompt()
            user_message = build_suggest_answer_user_message(
                user_text=user_input,
                history_events=history_events,
                knowledge_results=knowledge,
                baby_profile=baby_profile,
            )
        else:
            # 历史查询意图（默认）：使用历史回答提示词
            system_prompt = build_history_answer_system_prompt()
            user_message = build_history_answer_user_message(
                user_text=user_input,
                history_events=history_events,
            )

        # 调用 LLM 生成回答
        response = await llm_client.invoke(
            messages=[{"role": "user", "content": user_message}],
            model_config=model_config,
            system_prompt=system_prompt,
        )

        return {"response": response.content}

    except Exception as e:
        # LLM 调用失败，返回错误提示
        logger.error(f"回答生成 LLM 调用失败: {str(e)}")
        error_msg = "抱歉，生成回答时出现错误，请稍后再试。"
        return {"response": error_msg}

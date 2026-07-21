"""
流式回答生成节点

业务说明：
LangGraph 节点：用于诊疗场景的流式回答生成。
调用 LLM 流式接口，支持 thinking 模式（分离思考和回答内容）。
返回异步生成器，用于 SSE 流式输出。

设计思路：
1. 从 State 中读取 question、history_events、knowledge、baby_profile、model_config
2. 使用诊疗提示词构建系统提示词和用户消息
3. 调用 llm_client.stream 进行流式调用
4. 支持 thinking 模式
5. 返回异步生成器（注意：LangGraph 流式节点需要特殊处理）

注意：
由于 LangGraph 的 StateGraph 不直接支持节点返回异步生成器，
这个节点返回的是生成器函数，由路由层迭代调用。
实际上，clinic_graph 会使用 astream 模式，此节点作为流式节点存在。
"""

import logging
from typing import Any, AsyncGenerator, Dict

from app.clinic.graphs.nodes.prompts.clinic_answer import build_clinic_answer_system_prompt, build_clinic_answer_user_message
from app.shared.llm_client import LLMModelConfig, LLMResponse, llm_client

# 初始化日志记录器
logger = logging.getLogger(__name__)


async def stream_response(state: Dict[str, Any]) -> AsyncGenerator[LLMResponse, None]:
    """
    流式回答生成节点函数（生成器版本）

    业务逻辑：
    这是一个生成器函数，用于直接在路由层调用。
    由于 LangGraph StateGraph 的节点函数不支持直接返回异步生成器，
    在 clinic_graph 中实际使用时会用包装函数将生成器结果存入 state。
    此函数提供核心的流式调用逻辑。

    Args:
        state: 当前图状态（含 question, history_events, knowledge, baby_profile, model_config）

    Yields:
        LLMResponse 对象（流式逐块返回）
    """
    # 读取输入参数
    question = state.get("question", "")
    history_events = state.get("history_events", [])
    knowledge = state.get("knowledge", [])
    baby_profile = state.get("baby_profile", {})
    model_config_dict = state.get("model_config", {})

    # 构建模型配置对象
    model_config = LLMModelConfig(**model_config_dict)

    # 构建提示词
    system_prompt = build_clinic_answer_system_prompt()
    user_message = build_clinic_answer_user_message(
        question=question,
        history_events=history_events,
        knowledge_results=knowledge,
        baby_profile=baby_profile,
    )

    # 流式调用 LLM
    async for chunk in llm_client.stream(
        messages=[{"role": "user", "content": user_message}],
        model_config=model_config,
        system_prompt=system_prompt,
        thinking_enabled=True,
    ):
        yield chunk


async def stream_response_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    流式回答生成节点（StateGraph 兼容版本）

    业务逻辑：
    StateGraph 中的节点需要返回 dict，不能直接返回生成器。
    此函数将生成器的完整内容聚合后返回，用于同步模式。
    实际的流式输出在路由层直接调用 stream_response 生成器函数。

    Args:
        state: 当前图状态

    Returns:
        需要更新的 State 字段字典（response 字段）
    """
    response_parts = []
    async for chunk in stream_response(state):
        if chunk.content:
            response_parts.append(chunk.content)

    full_response = "".join(response_parts)
    return {"response": full_response}

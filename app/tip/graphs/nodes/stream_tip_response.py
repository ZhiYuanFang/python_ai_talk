"""
小贴士流式回答生成节点

业务说明：
用于小贴士场景的流式回答生成。
调用 LLM 流式接口，支持 thinking 模式（分离思考和回答内容）。
返回异步生成器，用于 SSE 流式输出。

设计思路：
1. 从 State 中读取 event_info、current_time、baby_age_months、history_events、knowledge、baby_profile、model_config
2. 使用小贴士提示词构建系统提示词和用户消息
3. 调用 llm_client.stream 进行流式调用
4. 支持 thinking 模式
5. 返回异步生成器，由路由层迭代调用

与 stream_response 的区别：
1. 提示词不同（tip_answer vs clinic_answer）
2. 读取的状态字段不同（event_info、baby_age_months、current_time vs question）
3. 上下文组装方式不同（以事件为中心 vs 以问题为中心）
"""

import logging
from typing import Any, AsyncGenerator, Dict

from app.tip.graphs.nodes.prompts.tip_answer import build_tip_answer_system_prompt, build_tip_answer_user_message
from app.shared.llm_client import LLMModelConfig, LLMResponse, llm_client

# 初始化日志记录器
logger = logging.getLogger(__name__)


async def stream_tip_response(state: Dict[str, Any]) -> AsyncGenerator[LLMResponse, None]:
    """
    小贴士流式回答生成器函数

    业务逻辑：
    1. 从 state 中读取事件信息、时间、月龄、历史、知识、宝宝画像、模型配置
    2. 构建小贴士专用的系统提示词和用户消息
    3. 调用 LLM 流式接口，支持 thinking 模式
    4. 逐块 yield LLMResponse 对象

    Args:
        state: 当前图状态（含 event_info, current_time, baby_age_months, history_events, knowledge, baby_profile, model_config）

    Yields:
        LLMResponse 对象（流式逐块返回，包含 thinking 和 content 字段）
    """
    # 读取输入参数
    event_info = state.get("event_info", {})           # 触发事件信息
    current_time = state.get("current_time", 0)        # 当前触发时间
    baby_age_months = state.get("baby_age_months", 0)  # 宝宝月龄
    history_events = state.get("history_events", [])   # 近期喂养历史记录
    knowledge = state.get("knowledge", [])             # 向量检索结果
    baby_profile = state.get("baby_profile", {})       # 宝宝画像
    model_config_dict = state.get("model_config", {})  # 模型配置

    # 构建模型配置对象
    model_config = LLMModelConfig(**model_config_dict)

    # 构建提示词
    system_prompt = build_tip_answer_system_prompt()
    user_message = build_tip_answer_user_message(
        event_info=event_info,
        current_time=current_time,
        baby_age_months=baby_age_months,
        history_events=history_events,
        knowledge_results=knowledge,
        baby_profile=baby_profile,
    )

    # 流式调用 LLM
    # 业务说明：thinking_enabled=True 启用思考模式，LLM 会先输出思考过程再输出回答
    async for chunk in llm_client.stream(
        messages=[{"role": "user", "content": user_message}],
        model_config=model_config,
        system_prompt=system_prompt,
        thinking_enabled=True,
    ):
        yield chunk

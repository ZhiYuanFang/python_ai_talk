"""
意图分析路由

业务说明：
提供 /v1/analyze/intent 接口，接收自然语言文本和设备编号，返回意图分析结果。
使用 LangGraph 的 intent_graph 编排意图分析流程：
1. 意图分类（LLM 调用）
2. 条件路由（根据意图类型）
3. 后处理（history/suggest 意图需要拉取历史、检索向量库、生成回答）

设计思路：
1. 构建 IntentState 初始状态
2. 获取事件字典并注入 state
3. 调用 intent_graph.invoke() 执行流程
4. 从最终状态提取意图结果，构建 IntentResponse
5. history/suggest 意图将 LLM 生成的回答填入 content 字段
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter

from app.graphs.intent_graph import intent_graph
from app.schemas.intent import IntentRequest, IntentResponse
from app.services.event_cache import event_cache

# 初始化日志记录器
logger = logging.getLogger(__name__)

# 创建路由实例
router = APIRouter(prefix="/analyze", tags=["意图分析"])


@router.post("/intent", response_model=IntentResponse, summary="意图分析")
async def analyze_intent(request: IntentRequest):
    """
    意图分析接口

    业务逻辑：
    1. 接收用户输入文本、设备编号和模型配置
    2. 从缓存获取事件字典
    3. 构建 IntentState 初始状态
    4. 调用 LangGraph 的 intent_graph 执行完整意图分析流程
    5. 从最终状态提取结果，构建 IntentResponse
    6. history/suggest 意图的回答从 state.response 中获取

    Args:
        request: 意图分析请求，包含 text、deviceNo、model

    Returns:
        IntentResponse 意图分析结果
    """
    # 记录请求日志
    logger.info(
        f"意图分析请求: device_no={request.device_no}, text={request.text[:50]}..."
    )

    # 1. 获取事件字典
    # 业务说明：事件字典用于 LLM 识别事件类型，24 小时 TTL 缓存
    event_dictionary = await event_cache.get_event_dictionary()

    # 2. 构建初始状态
    # 业务说明：将请求参数和事件字典注入 State
    initial_state: Dict[str, Any] = {
        "user_input": request.text,
        "device_no": request.device_no,
        "model_config": {
            "provider": request.model.provider,
            "name": request.model.name,
            "max_in_flight": request.model.max_in_flight,
        },
        "event_dictionary": event_dictionary,
    }

    # 3. 调用 LangGraph 执行意图分析流程
    # 业务说明：
    # - 第一步：意图分类
    # - feeding/conversation/exit：直接返回，不做后处理
    # - history：判断数据需求→拉取历史→生成回答
    # - suggest：判断数据需求→拉取历史→向量检索→宝宝画像→生成建议
    final_state = await intent_graph.ainvoke(initial_state)

    # 4. 从最终状态提取意图结果
    intent_result = final_state.get("intent_result", {})

    # 5. 构建响应
    # 业务说明：history/suggest 意图需要将生成的回答填入 content 字段
    response = IntentResponse(
        target_type=intent_result.get("target_type", "conversation"),
        action=intent_result.get("action", "reply"),
        event_name=intent_result.get("event_name", ""),
        keywords=intent_result.get("keywords", []),
        content=intent_result.get("content", ""),
    )

    # 6. 如果是 history 或 suggest 意图，将 LLM 生成的回答填入 content
    # 业务说明：
    # - history/suggest 意图走了后处理链路，回答在 state.response 中
    # - 其他意图的 content 已经在 intent_result 中（如 conversation 兜底文案）
    target_type = intent_result.get("target_type", "")
    if target_type in ("history", "suggest"):
        llm_response = final_state.get("response", "")
        if llm_response:
            response.content = llm_response

    # 记录响应日志
    logger.info(
        f"意图分析结果: target_type={response.target_type}, "
        f"action={response.action}"
    )

    return response

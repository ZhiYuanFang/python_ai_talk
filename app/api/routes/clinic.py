"""
诊疗流式路由

业务说明：
提供 /v1/clinic/stream 接口，接收诊疗问题，返回 SSE 流式响应。
使用 LangGraph 的 clinic_graph 准备上下文数据，然后流式生成回答。

流程：
1. 调用 clinic_graph 准备数据（判断数据需求→拉取历史→向量检索→获取宝宝画像）
2. 直接调用 stream_response 生成器进行流式输出
3. 将流式结果转换为 SSE 事件返回给客户端

设计思路：
1. clinic_graph 只负责数据准备（异步调用）
2. 流式回答在路由层直接生成（因为 StateGraph 不支持流式节点）
3. 支持 thinking 模式，分离思考和回答内容
"""

import json
import logging
from typing import Any, Dict, AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.graphs.clinic_graph import clinic_graph
from app.graphs.nodes.stream_response import stream_response
from app.schemas.intent import ClinicRequest, ClinicStreamResponse

# 初始化日志记录器
logger = logging.getLogger(__name__)

# 创建路由实例
router = APIRouter(prefix="/clinic", tags=["胖宝诊疗"])


@router.post("/stream", summary="胖宝诊疗（流式）")
async def clinic_stream(request: ClinicRequest):
    """
    胖宝诊疗流式接口

    业务逻辑：
    1. 接收诊疗问题、设备编号和模型配置
    2. 构建 ClinicState 初始状态
    3. 调用 clinic_graph 准备上下文数据（历史记录、向量知识、宝宝画像）
    4. 调用 stream_response 生成器流式生成回答
    5. 将流式结果包装为 SSE 事件返回

    Args:
        request: 诊疗请求，包含 question、deviceNo、model

    Returns:
        SSE 流式响应，包含 thinking 和 answer 两种事件类型
    """
    # 记录请求日志
    logger.info(
        f"诊疗请求: device_no={request.device_no}, question={request.question[:50]}..."
    )

    # 1. 构建初始状态
    initial_state: Dict[str, Any] = {
        "question": request.question,
        "device_no": request.device_no,
        "model_config": {
            "provider": request.model.provider,
            "name": request.model.name,
            "max_in_flight": request.model.max_in_flight,
        },
    }

    # 2. 调用 clinic_graph 准备上下文数据
    # 业务说明：
    # - 第一步：判断数据需求（需要哪些事件类型、多长时间范围）
    # - 第二步：按条件拉取历史记录（不再拉全量）
    # - 第三步：向量检索相关知识
    # - 第四步：获取宝宝画像
    final_state = await clinic_graph.ainvoke(initial_state)

    # 3. 将 question 放回 state（clinic_graph 的状态里有 question）
    # stream_response 需要 question 字段
    final_state["question"] = request.question
    final_state["model_config"] = {
        "provider": request.model.provider,
        "name": request.model.name,
        "max_in_flight": request.model.max_in_flight,
    }

    # 4. 生成 SSE 流式响应
    # 业务说明：使用 StreamingResponse 返回 SSE 格式数据
    return StreamingResponse(
        _stream_clinic_response(final_state),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream_clinic_response(
    state: Dict[str, Any],
) -> AsyncGenerator[str, None]:
    """
    生成诊疗流式 SSE 响应

    业务逻辑：
    调用 stream_response 生成器，将每个 LLM chunk 转换为 SSE 事件格式。
    支持 thinking 和 answer 两种事件类型。

    Args:
        state: 包含上下文数据的状态字典

    Yields:
        SSE 格式的字符串
    """
    async for chunk in stream_response(state):
        if chunk.thinking:
            # 思考事件
            event = ClinicStreamResponse(
                type="thinking",
                content=chunk.thinking,
            )
            yield f"data: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n"

        if chunk.content:
            # 回答事件
            event = ClinicStreamResponse(
                type="answer",
                content=chunk.content,
            )
            yield f"data: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n"

    # 流式结束标记
    yield "data: [DONE]\n\n"

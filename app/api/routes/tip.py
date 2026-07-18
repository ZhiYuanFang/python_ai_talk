"""
小贴士流式路由

业务说明：
提供 /v1/tip/stream 接口，接收小贴士生成请求，返回 SSE 流式响应。
使用 LangGraph 的 tip_graph 以流式方式准备上下文数据，然后流式生成小贴士回答。

流程：
1. 调用 tip_graph.astream() 流式执行数据准备节点（判断数据需求→拉取历史→向量检索→获取宝宝画像）
2. 每个节点完成时推送 thinking 事件，让用户实时感知 AI 思考过程
3. 节点全部完成后，推送 "正在生成回答..." thinking 事件
4. 调用 stream_tip_response 生成器流式输出 LLM 小贴士（thinking + answer 事件）
5. 推送 [DONE] 结束标记

设计思路：
1. tip_graph 用 astream 模式执行，节点级推送 thinking 事件
2. 流式回答在路由层直接生成（因为 StateGraph 不支持流式节点）
3. 支持 thinking 模式，分离思考和回答内容
4. SSE 格式与诊疗接口一致：{"type": "thinking|answer", "content": "..."}
"""

import json
import logging
from typing import Any, Dict, AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.graphs.tip_graph import tip_graph
from app.graphs.nodes.stream_tip_response import stream_tip_response
from app.graphs.nodes.thinking_messages import get_thinking_message
from app.schemas.tip import TipRequest, TipStreamResponse

# 初始化日志记录器
logger = logging.getLogger(__name__)

# 创建路由实例
router = APIRouter(prefix="/tip", tags=["小贴士"])


@router.post("/stream", summary="小贴士生成（流式）")
async def tip_stream(request: TipRequest):
    """
    小贴士生成流式接口

    业务逻辑：
    1. 接收触发事件信息、设备编号、宝宝月龄、当前时间和模型配置
    2. 构建 TipState 初始状态
    3. 使用 tip_graph.astream() 流式执行数据准备节点，每个节点推送 thinking 事件
    4. 节点全部完成后，推送 "正在生成回答..." thinking 事件
    5. 调用 stream_tip_response 生成器流式生成小贴士（thinking + answer 事件）
    6. 将流式结果包装为 SSE 事件返回

    Args:
        request: 小贴士请求，包含 event_id、event_name、deviceNo、babyAgeMonths、currentTime、model

    Returns:
        SSE 流式响应，包含 thinking（节点思考进度）和 answer（LLM 小贴士内容）两种事件类型
    """
    # 记录请求日志
    logger.info(
        f"小贴士请求: device_no={request.device_no}, event_name={request.event_name}"
    )

    # 1. 构建初始状态
    initial_state: Dict[str, Any] = {
        "event_info": {
            "event_id": request.event_id,
            "event_name": request.event_name,
        },
        "device_no": request.device_no,
        "current_time": request.current_time,
        "baby_age_months": request.baby_age_months,
        "model_config": {
            "provider": request.model.provider,
            "name": request.model.name,
            "max_in_flight": request.model.max_in_flight,
        },
    }

    # 2. 生成 SSE 流式响应
    # 业务说明：使用 StreamingResponse 返回 SSE 格式数据
    # 流式过程包含：节点级 thinking 事件 → LLM thinking/answer 事件 → [DONE]
    return StreamingResponse(
        _stream_tip_response(initial_state),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream_tip_response(
    initial_state: Dict[str, Any],
) -> AsyncGenerator[str, None]:
    """
    生成小贴士流式 SSE 响应（含节点级 thinking 事件）

    业务逻辑：
    1. 调用 tip_graph.astream() 流式执行图，每个节点完成时推送 thinking 事件
    2. 累积最终状态（历史记录、向量知识、宝宝画像）
    3. 图执行完成后，推送 "正在生成回答..." thinking 事件
    4. 调用 stream_tip_response 生成器流式输出 LLM 小贴士（thinking + answer 事件）
    5. 推送 [DONE] 结束标记

    Args:
        initial_state: 初始状态字典（含 event_info、device_no、current_time、baby_age_months、model_config）

    Yields:
        SSE 格式的字符串
    """
    # 累积最终状态的字典
    # 业务说明：astream 模式下每个节点返回增量更新，需要手动合并
    final_state: Dict[str, Any] = dict(initial_state)

    # 1. 流式执行 tip_graph，推送节点级 thinking 事件
    # 业务说明：astream(stream_mode="updates") 会在每个节点完成时 yield (node_name, update_dict)
    async for chunk in tip_graph.astream(initial_state, stream_mode="updates"):
        # LangGraph updates 模式 yield 的 chunk 格式因版本而异
        # 兼容处理：chunk 可能是 tuple (node_name, update_dict) 或 dict
        node_name = None
        update_dict = None

        if isinstance(chunk, tuple) and len(chunk) >= 2:
            # tuple 格式：(node_name, update_dict)
            node_name = chunk[0]
            update_dict = chunk[1]
        elif isinstance(chunk, dict):
            # dict 格式：可能包含 node 字段
            node_name = chunk.get("node") or chunk.get("name")
            update_dict = chunk.get("data") or chunk

        # 推送该节点的 thinking 事件
        if node_name:
            thinking_text = get_thinking_message(node_name)
            event = TipStreamResponse(type="thinking", content=thinking_text)
            yield f"data: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n"

        # 累积状态更新
        if update_dict and isinstance(update_dict, dict):
            final_state.update(update_dict)

    # 2. 推送 LLM 开始的 thinking 事件
    # 业务说明：数据准备完成，开始调用 LLM 生成小贴士
    llm_start_event = TipStreamResponse(
        type="thinking",
        content=get_thinking_message("llm_start"),
    )
    yield f"data: {json.dumps(llm_start_event.model_dump(), ensure_ascii=False)}\n\n"

    # 3. 调用 stream_tip_response 流式输出 LLM 小贴士
    # 业务说明：stream_tip_response 是生成器函数，逐块返回 LLM 的 thinking 和 answer 内容
    async for chunk in stream_tip_response(final_state):
        if chunk.thinking:
            # LLM 思考过程事件（DeepSeek thinking 模式的思考内容）
            event = TipStreamResponse(
                type="thinking",
                content=chunk.thinking,
            )
            yield f"data: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n"

        if chunk.content:
            # LLM 小贴士内容事件
            event = TipStreamResponse(
                type="answer",
                content=chunk.content,
            )
            yield f"data: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n"

    # 4. 流式结束标记
    yield "data: [DONE]\n\n"

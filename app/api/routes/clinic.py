"""
诊疗流式路由

业务说明：
提供 /v1/clinic/stream 接口，接收诊疗问题，返回 SSE 流式响应。
提供 /v1/clinic/feedback 接口，接收用户反馈，更新知识质量分。
使用 LangGraph 的 clinic_graph 以流式方式准备上下文数据，然后流式生成回答。

流程：
1. 调用 clinic_graph.astream() 流式执行数据准备节点（判断数据需求→拉取历史→向量检索→获取宝宝画像）
2. 每个节点开始执行时推送 thinking 事件，让用户实时感知 AI 思考过程
3. 节点全部完成后，推送 "正在生成回答..." thinking 事件
4. 调用 stream_response 生成器流式输出 LLM 回答（thinking + answer 事件）
5. 推送 done 事件（包含 answerId）
6. 用户反馈通过 /v1/clinic/feedback 接口提交，更新相关知识的质量分

设计思路：
1. clinic_graph 用 astream 模式执行，节点级推送 thinking 事件
2. 流式回答在路由层直接生成（因为 StateGraph 不支持流式节点）
3. 支持 thinking 模式，分离思考和回答内容
4. thinking 事件包含节点执行进度，answer 事件包含 LLM 回答内容
5. 反馈接口支持 answerId 和 feedback 值（1=👍，-1=👎），用于知识飞轮
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

from app.clinic.graphs.clinic_graph import clinic_graph
from app.clinic.graphs.nodes.stream_response import stream_response
from app.clinic.graphs.nodes.thinking_messages import get_thinking_message
from app.feeding.schemas.intent import ClinicRequest, ClinicStreamResponse
from app.shared.vector_store import vector_store

# 初始化日志记录器
logger = logging.getLogger(__name__)

# 创建路由实例
router = APIRouter(prefix="/clinic", tags=["胖宝诊疗"])

# 反馈频率限制存储（内存存储，服务重启后清空）
# 格式：{answer_id: {"last_feedback_time": datetime, "feedback_count": int}}
_feedback_limits: Dict[str, Dict[str, Any]] = {}

# 频率限制配置
MAX_FEEDBACK_PER_ANSWER = 5
FEEDBACK_TIME_WINDOW_MINUTES = 60


@router.post("/stream", summary="胖宝诊疗（流式）")
async def clinic_stream(request: ClinicRequest):
    """
    胖宝诊疗流式接口

    业务逻辑：
    1. 接收诊疗问题、设备编号和模型配置
    2. 构建 ClinicState 初始状态
    3. 使用 clinic_graph.astream() 流式执行数据准备节点，每个节点推送 thinking 事件
    4. 节点全部完成后，推送 "正在生成回答..." thinking 事件
    5. 调用 stream_response 生成器流式生成回答（thinking + answer 事件）
    6. 将流式结果包装为 SSE 事件返回

    Args:
        request: 诊疗请求，包含 question、deviceNo、model

    Returns:
        SSE 流式响应，包含 thinking（节点思考进度）和 answer（LLM 回答）两种事件类型
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

    # 2. 生成 SSE 流式响应
    # 业务说明：使用 StreamingResponse 返回 SSE 格式数据
    # 流式过程包含：节点级 thinking 事件 → LLM thinking/answer 事件 → [DONE]
    return StreamingResponse(
        _stream_clinic_response(initial_state),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream_clinic_response(
    initial_state: Dict[str, Any],
) -> AsyncGenerator[str, None]:
    """
    生成诊疗流式 SSE 响应（含节点级 thinking 事件）

    业务逻辑：
    1. 生成唯一的 answer_id
    2. 调用 clinic_graph.astream() 流式执行图，每个节点完成时推送 thinking 事件
    3. 累积最终状态（历史记录、向量知识、宝宝画像）
    4. 图执行完成后，推送 "正在生成回答..." thinking 事件
    5. 调用 stream_response 生成器流式输出 LLM 回答（thinking + answer 事件）
    6. 推送 done 事件（包含 answerId）

    Args:
        initial_state: 初始状态字典（含 question、device_no、model_config）

    Yields:
        SSE 格式的字符串
    """
    # 生成唯一的 answer_id，用于后续反馈
    answer_id = f"clinic_{uuid.uuid4().hex[:12]}"

    # 累积最终状态的字典
    # 业务说明：astream 模式下每个节点返回增量更新，需要手动合并
    final_state: Dict[str, Any] = dict(initial_state)

    # 1. 流式执行 clinic_graph，推送节点级 thinking 事件
    # 业务说明：astream(stream_mode="updates") 会在每个节点完成时 yield (node_name, update_dict)
    async for chunk in clinic_graph.astream(initial_state, stream_mode="updates"):
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
            event = ClinicStreamResponse(type="thinking", content=thinking_text)
            yield f"data: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n"

        # 累积状态更新
        if update_dict and isinstance(update_dict, dict):
            final_state.update(update_dict)

    # 2. 推送 LLM 开始的 thinking 事件
    # 业务说明：数据准备完成，开始调用 LLM 生成回答
    llm_start_event = ClinicStreamResponse(
        type="thinking",
        content=get_thinking_message("llm_start"),
    )
    yield f"data: {json.dumps(llm_start_event.model_dump(), ensure_ascii=False)}\n\n"

    # 3. 调用 stream_response 流式输出 LLM 回答
    # 业务说明：stream_response 是生成器函数，逐块返回 LLM 的 thinking 和 answer 内容
    async for chunk in stream_response(final_state):
        if chunk.thinking:
            # LLM 思考过程事件（DeepSeek thinking 模式的思考内容）
            event = ClinicStreamResponse(
                type="thinking",
                content=chunk.thinking,
            )
            yield f"data: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n"

        if chunk.content:
            # LLM 回答内容事件
            event = ClinicStreamResponse(
                type="answer",
                content=chunk.content,
            )
            yield f"data: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n"

    # 4. 推送 done 事件（包含 answerId，用于后续反馈）
    done_event = ClinicStreamResponse(
        type="done",
        content="回答完成",
        answer_id=answer_id,
    )
    yield f"data: {json.dumps(done_event.model_dump(), ensure_ascii=False)}\n\n"


def _check_feedback_limit(answer_id: str) -> bool:
    """
    检查反馈频率限制

    业务逻辑：
    1. 检查该 answer_id 在时间窗口内的反馈次数
    2. 如果超过限制，返回 False；否则返回 True
    3. 更新反馈计数和时间

    Args:
        answer_id: 回答 ID

    Returns:
        是否允许反馈
    """
    now = datetime.now()
    limit_info = _feedback_limits.get(answer_id)

    if limit_info:
        time_diff = (now - limit_info["last_feedback_time"]).total_seconds() / 60
        if time_diff > FEEDBACK_TIME_WINDOW_MINUTES:
            _feedback_limits[answer_id] = {
                "last_feedback_time": now,
                "feedback_count": 1,
            }
            return True

        if limit_info["feedback_count"] >= MAX_FEEDBACK_PER_ANSWER:
            return False

        limit_info["feedback_count"] += 1
        return True
    else:
        _feedback_limits[answer_id] = {
            "last_feedback_time": now,
            "feedback_count": 1,
        }
        return True


@router.post("/feedback", summary="诊疗反馈")
async def clinic_feedback(answer_id: str, feedback: int):
    """
    诊疗反馈接口

    业务逻辑：
    1. 验证反馈参数（feedback 必须为 1 或 -1）
    2. 检查反馈频率限制
    3. 根据 answer_id 更新相关知识的质量分
    4. 返回反馈结果

    Args:
        answer_id: 回答 ID（由流式响应的 done 事件返回）
        feedback: 反馈值，1=👍，-1=👎

    Returns:
        包含反馈结果的 JSON 响应
    """
    if feedback not in [1, -1]:
        raise HTTPException(status_code=400, detail="反馈值必须为 1（👍）或 -1（👎）")

    if not _check_feedback_limit(answer_id):
        raise HTTPException(
            status_code=429,
            detail=f"该回答的反馈次数已达上限（{MAX_FEEDBACK_PER_ANSWER}次/{FEEDBACK_TIME_WINDOW_MINUTES}分钟）",
        )

    try:
        vector_store.update_quality_score(answer_id, feedback)

        logger.info(f"诊疗反馈成功: answer_id={answer_id}, feedback={feedback}")

        return JSONResponse(content={
            "code": 0,
            "message": "反馈成功",
            "data": {
                "answer_id": answer_id,
                "feedback": feedback,
            },
        })
    except Exception as e:
        logger.error(f"诊疗反馈失败: {str(e)}")
        raise HTTPException(status_code=500, detail="反馈处理失败")

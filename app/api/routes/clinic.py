"""
陪伴续聊流式路由（clinic）

业务说明：
提供 /v1/clinic/stream：家长续聊，与 tip 共享按 device_no 的 Python Redis 会话。
提供 /v1/clinic/feedback：显式反馈兼容通道（主路径为隐式采纳判定）。
数据准备由 clinic_graph 统一编排；流式经 custom thinking 逐步字幕，非流式可 ainvoke 同图。

流程：
1. 读陪伴会话，注入近轮 chat_context
2. clinic_graph.astream（飞轮 + 门禁 + 准备）→ thinking SSE
3. 流式生成闺蜜口语回答并写回会话
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator, Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from app.clinic.graphs.clinic_graph import clinic_graph
from app.clinic.graphs.nodes.stream_response import stream_response
from app.clinic.graphs.nodes.thinking_messages import get_thinking_message
from app.feeding.schemas.intent import ClinicRequest, ClinicStreamResponse
from app.feeding.services.event_cache import event_cache
from app.shared.companion_session import (
    companion_session_store,
    extract_knowledge_ids,
    format_chat_turns_for_prompt,
)
from app.shared.graphs.stream_graph import iter_graph_custom_thinking
from app.shared.schemas.feedback import FeedbackRequest
from app.shared.vector_store import vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clinic", tags=["智能陪伴"])

_feedback_limits: Dict[str, Dict[str, Any]] = {}
MAX_FEEDBACK_PER_ANSWER = 5
FEEDBACK_TIME_WINDOW_MINUTES = 60


@router.post("/stream", summary="智能陪伴续聊（流式）")
async def clinic_stream(request: ClinicRequest):
    """
    陪伴续聊流式接口。

    业务逻辑：
    与 tip 共享 device_no 会话；clinic_graph 编排准备并推送逐步 thinking；流式返回回答。
    """
    logger.info(
        f"陪伴续聊请求: device_no={request.device_no}, question={request.question[:50]}..."
    )

    event_dictionary = await event_cache.get_event_dictionary()

    session = await companion_session_store.get(request.device_no)
    chat_context = format_chat_turns_for_prompt(session.turns)

    initial_state: Dict[str, Any] = {
        "question": request.question,
        "device_no": request.device_no,
        "model_config": {
            "provider": request.model.provider,
            "name": request.model.name,
            "max_in_flight": request.model.max_in_flight,
        },
        "event_dictionary": event_dictionary,
        "chat_context": chat_context,
    }

    return StreamingResponse(
        _stream_clinic_response(initial_state, session_device_no=request.device_no),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream_clinic_response(
    initial_state: Dict[str, Any],
    *,
    session_device_no: str,
) -> AsyncGenerator[str, None]:
    """生成 clinic SSE：clinic_graph custom thinking → 流式回答 → 写会话。"""
    answer_id = f"clinic_{uuid.uuid4().hex[:12]}"
    final_state: Dict[str, Any] = dict(initial_state)
    question = str(initial_state.get("question") or "")

    async for kind, payload in iter_graph_custom_thinking(clinic_graph, initial_state):
        if kind == "thinking":
            event = ClinicStreamResponse(
                type="thinking",
                content=str(payload.get("content") or ""),
            )
            yield f"data: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n"
        elif kind == "final":
            final_state = dict(payload)

    llm_start_event = ClinicStreamResponse(
        type="thinking",
        content=get_thinking_message("llm_start"),
    )
    yield f"data: {json.dumps(llm_start_event.model_dump(), ensure_ascii=False)}\n\n"

    answer_parts: list[str] = []
    async for chunk in stream_response(final_state):
        if chunk.thinking:
            event = ClinicStreamResponse(type="thinking", content=chunk.thinking)
            yield f"data: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n"

        if chunk.content:
            answer_parts.append(chunk.content)
            event = ClinicStreamResponse(type="answer", content=chunk.content)
            yield f"data: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n"

    full_answer = "".join(answer_parts)
    knowledge_ids = extract_knowledge_ids(final_state.get("knowledge"))

    try:
        await companion_session_store.append_turn(
            session_device_no,
            user=question,
            assistant=full_answer,
            source="clinic",
            answer_id=answer_id,
            knowledge_ids=knowledge_ids,
            suggestion_text=full_answer,
        )
    except Exception as e:
        logger.warning(f"写入陪伴会话失败（不中断 SSE）: {e}")

    done_event = ClinicStreamResponse(
        type="done",
        content="回答完成",
        answer_id=answer_id,
    )
    yield f"data: {json.dumps(done_event.model_dump(), ensure_ascii=False)}\n\n"


def _check_feedback_limit(answer_id: str) -> bool:
    """显式反馈频率限制（兼容旧客户端）。"""
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

    _feedback_limits[answer_id] = {
        "last_feedback_time": now,
        "feedback_count": 1,
    }
    return True


@router.post("/feedback", summary="陪伴反馈（显式兼容）")
async def clinic_feedback(request: FeedbackRequest):
    """
    显式反馈接口（保留）。

    主路径为 clinic 续聊时的隐式采纳判定；本接口供旧客户端 👍/👎。
    """
    if not _check_feedback_limit(request.answer_id):
        raise HTTPException(
            status_code=429,
            detail=(
                f"该回答的反馈次数已达上限"
                f"（{MAX_FEEDBACK_PER_ANSWER}次/{FEEDBACK_TIME_WINDOW_MINUTES}分钟）"
            ),
        )

    try:
        vector_store.update_quality_score(request.answer_id, request.feedback)

        logger.info(
            f"陪伴显式反馈成功: answer_id={request.answer_id}, "
            f"feedback={request.feedback}"
        )

        return JSONResponse(
            content={
                "code": 0,
                "message": "反馈成功",
                "data": {
                    "answer_id": request.answer_id,
                    "feedback": request.feedback,
                },
            }
        )
    except Exception as e:
        logger.error(f"陪伴显式反馈失败: {str(e)}")
        raise HTTPException(status_code=500, detail="反馈处理失败")

"""
陪伴续聊流式路由（clinic）

业务说明：
提供 /v1/clinic/stream：家长续聊，与 tip 共享按 device_no 的 Python Redis 会话。
知识飞轮仅依赖多轮隐式采纳（已下线显式 /feedback；Go/Flutter 旧调用将 404）。
数据准备由 clinic_graph 统一编排；命中 Q&A 捷径时跳过完整 LLM 生成。
"""

import json
import logging
import uuid
from typing import Any, AsyncGenerator, Dict

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.clinic.graphs.clinic_graph import clinic_graph
from app.clinic.graphs.nodes.generate_clinic_answer import generate_clinic_answer
from app.clinic.graphs.nodes.stream_response import stream_response
from app.clinic.graphs.nodes.thinking_messages import get_thinking_message
from app.feeding.schemas.intent import ClinicRequest, ClinicStreamResponse, ClinicSyncResponse
from app.feeding.services.event_cache import event_cache
from app.shared.baby_age import age_band_from_months
from app.shared.companion_session import (
    companion_session_store,
    derive_history_grounded,
    extract_knowledge_ids,
    format_chat_turns_for_prompt,
)
from app.shared.graphs.node_thinking import ensure_orchestration_thinking_content
from app.shared.graphs.stream_graph import iter_graph_custom_thinking

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clinic", tags=["智能陪伴"])


def _clinic_model_dict(request: ClinicRequest) -> Dict[str, Any]:
    """非流式可省略 model，走保底序。"""
    if request.model is None:
        return {}
    return {
        "provider": request.model.provider,
        "name": request.model.name,
        "max_in_flight": request.model.max_in_flight,
    }


@router.post("", response_model=ClinicSyncResponse, summary="智能陪伴（非流式）")
async def clinic_sync(request: ClinicRequest):
    """
    非流式陪伴：与 /clinic/stream 共用 clinic_graph，返回 answer/answer_id。
    不走意图图，不写喂养记录。
    """
    logger.info(
        f"非流式陪伴: device_no={request.device_no}, question={request.question[:50]}..."
    )
    event_dictionary = await event_cache.get_event_dictionary()
    session = await companion_session_store.get(request.device_no)
    chat_context = format_chat_turns_for_prompt(session.turns)
    initial_state: Dict[str, Any] = {
        "question": request.question,
        "device_no": request.device_no,
        "model_config": _clinic_model_dict(request),
        "event_dictionary": event_dictionary,
        "chat_context": chat_context,
    }
    final_state = await clinic_graph.ainvoke(initial_state)
    # 捷径命中用库内答案；否则同步生成（与 stream 同提示词）
    answer = str(final_state.get("qa_answer") or "").strip()
    if not answer:
        try:
            gen = await generate_clinic_answer(final_state)
            answer = str(gen.get("response") or "").strip()
            final_state.update(gen)
        except Exception as e:
            logger.error(f"非流式陪伴生成失败: {e}", exc_info=True)
            answer = ""
    if not answer:
        answer = "我在，你再说具体一点。"
    answer_id = f"clinic_{uuid.uuid4().hex[:12]}"
    try:
        await companion_session_store.append_turn(
            request.device_no,
            user=request.question,
            assistant=answer,
            source="clinic",
            answer_id=answer_id,
            knowledge_ids=extract_knowledge_ids(final_state.get("knowledge")),
            suggestion_text=answer,
            standalone_question=final_state.get("standalone_question") or "",
            age_band=final_state.get("age_band")
            or age_band_from_months(final_state.get("baby_age_months"))
            or "",
            history_grounded=derive_history_grounded(final_state),
            qa_match_id=(
                str(final_state.get("qa_match_id") or "")
                if final_state.get("qa_hit")
                else ""
            ),
        )
    except Exception as e:
        logger.warning(f"写入陪伴会话失败（不中断）: {e}")
    return ClinicSyncResponse(answer=answer, answer_id=answer_id)


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
        "model_config": _clinic_model_dict(request),
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
    """生成 clinic SSE：clinic_graph custom thinking → 流式/捷径回答 → 写会话。"""
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

    answer_parts: list[str] = []
    if final_state.get("qa_hit") and str(final_state.get("qa_answer") or "").strip():
        logger.info(
            "clinic 流式走 Q&A 捷径: id=%s, sim=%s",
            final_state.get("qa_match_id"),
            final_state.get("qa_match_score"),
        )
        full_answer = str(final_state.get("qa_answer") or "").strip()
        answer_parts.append(full_answer)
        event = ClinicStreamResponse(type="answer", content=full_answer)
        yield f"data: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n"
    else:
        llm_start_event = ClinicStreamResponse(
            type="thinking",
            content=ensure_orchestration_thinking_content(
                get_thinking_message("llm_start")
            ),
        )
        yield f"data: {json.dumps(llm_start_event.model_dump(), ensure_ascii=False)}\n\n"

        # 本流首次 LLM thinking 需段首 \r 开新气泡；其后原样追加
        first_llm_thinking = True
        async for chunk in stream_response(final_state):
            if chunk.thinking:
                thinking_text = chunk.thinking
                if first_llm_thinking:
                    thinking_text = ensure_orchestration_thinking_content(thinking_text)
                    first_llm_thinking = False
                event = ClinicStreamResponse(type="thinking", content=thinking_text)
                yield f"data: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n"

            if chunk.content:
                answer_parts.append(chunk.content)
                event = ClinicStreamResponse(type="answer", content=chunk.content)
                yield f"data: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n"

    full_answer = "".join(answer_parts)
    knowledge_ids = extract_knowledge_ids(final_state.get("knowledge"))
    age_band = final_state.get("age_band") or age_band_from_months(
        final_state.get("baby_age_months")
    )

    try:
        await companion_session_store.append_turn(
            session_device_no,
            user=question,
            assistant=full_answer,
            source="clinic",
            answer_id=answer_id,
            knowledge_ids=knowledge_ids,
            suggestion_text=full_answer,
            standalone_question=final_state.get("standalone_question") or "",
            age_band=age_band or "",
            history_grounded=derive_history_grounded(final_state),
            qa_match_id=(
                str(final_state.get("qa_match_id") or "")
                if final_state.get("qa_hit")
                else ""
            ),
        )
    except Exception as e:
        logger.warning(f"写入陪伴会话失败（不中断 SSE）: {e}")

    done_event = ClinicStreamResponse(
        type="done",
        content="回答完成",
        answer_id=answer_id,
    )
    yield f"data: {json.dumps(done_event.model_dump(), ensure_ascii=False)}\n\n"

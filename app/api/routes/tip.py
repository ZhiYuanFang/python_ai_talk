"""
事件开场陪伴流式路由（tip）

业务说明：
提供 /v1/tip/stream：添加事件后闺蜜先开口，写入按 device_no 的 Python Redis 会话。
与 /v1/clinic/stream 共享同一陪伴会话；知识飞轮仅依赖多轮隐式采纳
（已下线显式 /feedback；Go/Flutter 旧调用将 404）。

流程：
1. 读会话近轮注入 chat_context
2. tip_graph.astream 数据准备（预置 data_requirement，入口 fetch_history）
3. 流式生成口语开场
4. 合成 user「刚记录了「事件」」+ assistant 写入会话；last_suggestion 待隐式飞轮
"""

import json
import logging
import uuid
from typing import Any, AsyncGenerator, Dict

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.clinic.graphs.nodes.thinking_messages import get_thinking_message
from app.feeding.services.event_cache import event_cache
from app.shared.baby_age import age_band_from_months
from app.shared.companion_session import (
    build_tip_synthetic_user,
    companion_session_store,
    extract_knowledge_ids,
    format_chat_turns_for_prompt,
)
from app.shared.graphs.node_thinking import ensure_orchestration_thinking_content
from app.shared.graphs.stream_graph import iter_graph_custom_thinking
from app.tip.graphs.nodes.stream_tip_response import stream_tip_response
from app.tip.graphs.tip_graph import tip_graph
from app.tip.schemas.tip import TipRequest, TipStreamResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tip", tags=["事件开场陪伴"])


@router.post("/stream", summary="事件开场陪伴（流式）")
async def tip_stream(request: TipRequest):
    """
    tip 开场流式接口。

    业务逻辑：
    事件触发后生成口语陪伴；写入共享会话供 clinic 续聊与隐式飞轮。
    """
    logger.info(
        f"事件开场请求: device_no={request.device_no}, event_name={request.event_name}"
    )

    event_dictionary = await event_cache.get_event_dictionary()
    session = await companion_session_store.get(request.device_no)
    chat_context = format_chat_turns_for_prompt(session.turns)

    initial_state: Dict[str, Any] = {
        "event_info": {
            "event_id": request.event_id,
            "event_name": request.event_name,
        },
        "question": request.event_name,
        "device_no": request.device_no,
        "model_config": {
            "provider": request.model.provider,
            "name": request.model.name,
            "max_in_flight": request.model.max_in_flight,
        },
        "event_dictionary": event_dictionary,
        "chat_context": chat_context,
        "data_requirement": {
            "event_ids": [request.event_id],
            "time_range": "last_7_days",
            "limit": 20,
        },
    }

    return StreamingResponse(
        _stream_tip_response(initial_state, request=request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream_tip_response(
    initial_state: Dict[str, Any],
    *,
    request: TipRequest,
) -> AsyncGenerator[str, None]:
    """生成 tip SSE：tip_graph custom thinking → 流式回答 → 写共享会话。"""
    answer_id = f"tip_{uuid.uuid4().hex[:12]}"
    final_state: Dict[str, Any] = dict(initial_state)

    async for kind, payload in iter_graph_custom_thinking(tip_graph, initial_state):
        if kind == "thinking":
            event = TipStreamResponse(
                type="thinking",
                content=str(payload.get("content") or ""),
            )
            yield f"data: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n"
        elif kind == "final":
            final_state = dict(payload)

    llm_start_event = TipStreamResponse(
        type="thinking",
        content=ensure_orchestration_thinking_content(
            get_thinking_message("llm_start")
        ),
    )
    yield f"data: {json.dumps(llm_start_event.model_dump(), ensure_ascii=False)}\n\n"

    answer_parts: list[str] = []
    async for chunk in stream_tip_response(final_state):
        # LLM thinking 原样转发，不加尾部换行
        if chunk.thinking:
            event = TipStreamResponse(type="thinking", content=chunk.thinking)
            yield f"data: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n"

        if chunk.content:
            answer_parts.append(chunk.content)
            event = TipStreamResponse(type="answer", content=chunk.content)
            yield f"data: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n"

    full_answer = "".join(answer_parts)
    knowledge_ids = extract_knowledge_ids(final_state.get("knowledge"))
    age_band = age_band_from_months(final_state.get("baby_age_months"))

    try:
        await companion_session_store.append_turn(
            request.device_no,
            user=build_tip_synthetic_user(request.event_name),
            assistant=full_answer,
            source="tip",
            answer_id=answer_id,
            knowledge_ids=knowledge_ids,
            suggestion_text=full_answer,
            age_band=age_band or "",
        )
    except Exception as e:
        logger.warning(f"写入陪伴会话失败（不中断 SSE）: {e}")

    done_event = TipStreamResponse(
        type="done",
        content="回答完成",
        answer_id=answer_id,
    )
    yield f"data: {json.dumps(done_event.model_dump(), ensure_ascii=False)}\n\n"

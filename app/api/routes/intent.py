"""
意图分析路由

业务说明：
提供 /v1/analyze/intent 与 /v1/analyze/intent/stream，同一套意图图与后处理。
非流式不再伪装 clinic。陪伴走 /v1/clinic。
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.feeding.graphs.intent_graph import intent_graph
from app.feeding.schemas.intent import IntentRequest, IntentResponse, IntentStreamResponse
from app.feeding.services.clarification import create_leaf_confirm_pending
from app.feeding.services.event_cache import event_cache
from app.feeding.services.intent_pipeline import (
    build_intent_response_from_fields,
    postprocess_feeding_result,
    response_from_pending,
    try_exact_parent_disambiguation,
    try_handle_pending,
)
from app.shared.constants import IntentAction, TargetType
from app.shared.graphs.stream_graph import iter_graph_custom_thinking

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyze", tags=["意图分析"])


def _run_config(thread_id: str) -> Dict[str, Any]:
    """构建 LangGraph RunnableConfig。"""
    return {"configurable": {"thread_id": thread_id}}


def _model_config_dict(request: IntentRequest) -> Dict[str, Any]:
    """请求未带 model 时返回空 dict，供 llm_client 走纯保底序。"""
    if request.model is None:
        return {}
    return {
        "provider": request.model.provider,
        "name": request.model.name,
        "max_in_flight": request.model.max_in_flight,
    }


def _build_intent_response(intent_result: Dict[str, Any]) -> IntentResponse:
    """兼容旧字段字典构建响应。"""
    return build_intent_response_from_fields(intent_result)


async def _prepare_dictionaries() -> tuple[list, list]:
    """返回 (full, leaves)。"""
    full = await event_cache.get_full_event_dictionary()
    leaves = await event_cache.get_event_dictionary()
    return full, leaves


async def _run_cold_intent(
    *,
    text: str,
    device_no: str,
    model_config: Dict[str, Any],
    full_events: list,
    leaf_events: list,
) -> IntentResponse:
    """冷启动意图流程：父名检测 → 图执行 → feeding 后处理（供流式使用）。"""
    # 精确父名 → 强制消歧
    parent_resp = try_exact_parent_disambiguation(
        text,
        full_events,
        device_no=device_no,
        model_config=model_config,
    )
    if parent_resp is not None:
        return parent_resp

    thread_id = str(uuid4())
    initial_state: Dict[str, Any] = {
        "user_input": text,
        "device_no": device_no,
        "model_config": model_config,
        "event_dictionary": leaf_events,
        "event_dictionary_full": full_events,
        "conversation_id": thread_id,
    }

    final_state = await intent_graph.ainvoke(
        initial_state, config=_run_config(thread_id)
    )
    return _response_from_final_state(
        final_state,
        full_events=full_events,
        user_input=text,
        device_no=device_no,
        model_config=model_config,
    )


def _response_from_final_state(
    final_state: Dict[str, Any],
    *,
    full_events: list,
    user_input: str,
    device_no: str,
    model_config: Dict[str, Any],
) -> IntentResponse:
    """从图最终状态构建响应，feeding 走叶子校验/消歧。"""
    intent_result = dict(final_state.get("intent_result") or {})
    match_source = final_state.get("match_source") or intent_result.get("match_source")
    if match_source:
        intent_result["match_source"] = match_source
    if final_state.get("match_confidence") is not None:
        intent_result["match_confidence"] = final_state.get("match_confidence")

    target_type = intent_result.get("target_type", TargetType.CONVERSATION.value)
    need_confirm = bool(final_state.get("need_confirm", False))
    matched_vector_id = final_state.get("matched_vector_id", "") or ""

    if target_type == TargetType.FEEDING.value:
        return postprocess_feeding_result(
            intent_result,
            full_events=full_events,
            user_input=user_input,
            device_no=device_no,
            model_config=model_config,
            need_confirm=need_confirm,
            matched_vector_id=matched_vector_id,
        )

    # 查记录确认（如 AD → 营养品）
    if need_confirm and target_type == TargetType.HISTORY.value:
        pending = create_leaf_confirm_pending(
            leaf={
                "event_id": intent_result.get("event_id") or "",
                "event_name": intent_result.get("event_name") or "",
                "extra_names": [],
            },
            original_utterance=user_input,
            action=IntentAction.SEARCH.value,
            match_source=str(match_source or ""),
            device_no=device_no,
            model_config=model_config,
            events=intent_result.get("events") or [],
            op="read",
            remark_keyword=intent_result.get("remark_keyword") or "",
            confirm_message=intent_result.get("confirm_message")
            or final_state.get("confirm_message")
            or "请确认是否查询该事件的历史？",
        )
        return response_from_pending(pending)

    response = _build_intent_response(intent_result)
    llm_response = final_state.get("response", "")
    if llm_response and not response.content:
        response.content = llm_response
    return response


@router.post("/intent", response_model=IntentResponse, summary="意图分析")
async def analyze_intent(request: IntentRequest):
    """
    非流式意图分析：与 stream 同一套 pending / 图 / 后处理。
    """
    logger.info(
        f"非流式意图: device_no={request.device_no}, "
        f"text={request.text[:50]}..., conversation_id={request.conversation_id}"
    )
    full_events, leaf_events = await _prepare_dictionaries()
    model_config = _model_config_dict(request)

    if request.conversation_id:
        pending_resp, _as_new = await try_handle_pending(
            request.text, request.conversation_id, full_events
        )
        if pending_resp is not None:
            return pending_resp

    return await _run_cold_intent(
        text=request.text,
        device_no=request.device_no,
        model_config=model_config,
        full_events=full_events,
        leaf_events=leaf_events,
    )


@router.post("/intent/stream", summary="意图分析（流式）")
async def analyze_intent_stream(request: IntentRequest):
    """
    意图分析流式接口。

    与非流式 /intent 同一套 pending / 父消歧 / intent_graph。
    冷启动时推送节点 thinking。
    """
    logger.info(
        f"意图分析流式请求: device_no={request.device_no}, text={request.text[:50]}..., "
        f"conversation_id={request.conversation_id}"
    )

    full_events, leaf_events = await _prepare_dictionaries()
    model_config = _model_config_dict(request)

    # pending 续聊：无图节点，直接返回 answer
    if request.conversation_id:
        pending_resp, as_new = await try_handle_pending(
            request.text, request.conversation_id, full_events
        )
        if pending_resp is not None:

            async def _pending_sse() -> AsyncGenerator[str, None]:
                answer_event = IntentStreamResponse(
                    type="answer",
                    content=json.dumps(pending_resp.model_dump(), ensure_ascii=False),
                )
                yield f"data: {json.dumps(answer_event.model_dump(), ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(
                _pending_sse(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

    # 精确父名：直接消歧，无图
    parent_resp = try_exact_parent_disambiguation(
        request.text,
        full_events,
        device_no=request.device_no,
        model_config=model_config,
    )
    if parent_resp is not None:

        async def _parent_sse() -> AsyncGenerator[str, None]:
            answer_event = IntentStreamResponse(
                type="answer",
                content=json.dumps(parent_resp.model_dump(), ensure_ascii=False),
            )
            yield f"data: {json.dumps(answer_event.model_dump(), ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            _parent_sse(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    thread_id = str(uuid4())
    initial_state: Dict[str, Any] = {
        "user_input": request.text,
        "device_no": request.device_no,
        "model_config": model_config,
        "event_dictionary": leaf_events,
        "event_dictionary_full": full_events,
        "conversation_id": thread_id,
    }

    return StreamingResponse(
        _stream_intent_response(initial_state, thread_id, full_events, model_config),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream_intent_response(
    initial_state: Dict[str, Any],
    thread_id: str,
    full_events: list,
    model_config: Dict[str, Any],
) -> AsyncGenerator[str, None]:
    """
    冷启动流式：intent_graph.astream(custom+updates) 逐步 thinking，再组装 answer。

    非流式仍走 intent_graph.ainvoke（同一张图）。
    """
    final_state: Dict[str, Any] = dict(initial_state)
    # thread_id 仍写入 conversation_id（initial_state）；无 checkpointer 时 config 可省略
    _ = thread_id

    async for kind, payload in iter_graph_custom_thinking(intent_graph, initial_state):
        if kind == "thinking":
            event = IntentStreamResponse(
                type="thinking",
                content=str(payload.get("content") or ""),
                node=str(payload.get("node") or "") or None,
            )
            yield f"data: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n"
        elif kind == "final":
            final_state = dict(payload)

    response = _response_from_final_state(
        final_state,
        full_events=full_events,
        user_input=initial_state.get("user_input", ""),
        device_no=initial_state.get("device_no", ""),
        model_config=model_config,
    )

    answer_event = IntentStreamResponse(
        type="answer",
        content=json.dumps(response.model_dump(), ensure_ascii=False),
    )
    yield f"data: {json.dumps(answer_event.model_dump(), ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"

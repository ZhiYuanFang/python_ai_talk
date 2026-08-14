"""
意图分析路由

业务说明：
提供 /v1/analyze/intent 与 /v1/analyze/intent/stream，同一套意图图与后处理。
非流式不再伪装 clinic。陪伴走 /v1/clinic。
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.feeding.graphs.intent_graph import intent_graph
from app.feeding.graphs.states.intent_state import IntentState
from app.feeding.schemas.intent import IntentRequest, IntentResponse, IntentStreamResponse
from app.feeding.schemas.intent_result import coerce_intent_result
from app.feeding.services.event_cache import event_cache
from app.feeding.services.intent_pipeline import (
    build_intent_response_from_fields,
    create_history_confirm_response,
    postprocess_feeding_result,
    response_from_pending,
    try_exact_parent_disambiguation,
    try_handle_pending,
)
from app.shared.constants import TargetType
from app.shared.graphs.state_patch import ensure_model
from app.shared.graphs.stream_graph import iter_graph_custom_thinking

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyze", tags=["意图分析"])


def _run_config(thread_id: str) -> Dict[str, Any]:
    """构建 LangGraph RunnableConfig。"""
    return {"configurable": {"thread_id": thread_id}}


def _model_config_dict(request: IntentRequest) -> Dict[str, Any]:
    """从请求取出 Go 传入的唯一 model（必填）。"""
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
    initial_state = IntentState(
        user_input=text,
        device_no=device_no,
        llm_model=model_config,
        event_dictionary=leaf_events,
        event_dictionary_full=full_events,
        conversation_id=thread_id,
    )

    # 仅序列化边界：LangGraph ainvoke 入口需 dict
    final_state = await intent_graph.ainvoke(
        initial_state.model_dump(), config=_run_config(thread_id)
    )
    return _response_from_final_state(
        final_state,
        full_events=full_events,
        user_input=text,
        device_no=device_no,
        model_config=model_config,
    )


def _response_from_final_state(
    final_state: Any,
    *,
    full_events: list,
    user_input: str,
    device_no: str,
    model_config: Dict[str, Any],
) -> IntentResponse:
    """从图最终状态构建响应，feeding 走叶子校验/消歧。"""
    st = ensure_model(final_state, IntentState)
    ir = coerce_intent_result(st.intent_result)
    intent_result = ir.to_plain_dict()
    match_source = st.match_source or intent_result.get("match_source")
    if match_source:
        intent_result["match_source"] = match_source
    if st.match_confidence is not None:
        intent_result["match_confidence"] = st.match_confidence

    # 备注反查多命中已建 pending：直接返回，勿再走叶子软确认覆盖
    confirm_type = st.confirm_type or intent_result.get("confirm_type") or ""
    if confirm_type == "parent_disambiguation" and intent_result.get("options"):
        if st.conversation_id:
            intent_result["conversation_id"] = st.conversation_id
        intent_result["need_confirm"] = True
        return _build_intent_response(intent_result)

    # 零命中无法识别：conversation 短回复，不进确认
    if (
        intent_result.get("target_type") == TargetType.CONVERSATION.value
        and (intent_result.get("content") or "").startswith("无法识别对应的事件")
    ):
        return _build_intent_response(intent_result)

    target_type = intent_result.get("target_type", TargetType.CONVERSATION.value)
    need_confirm = bool(st.need_confirm)
    matched_vector_id = st.matched_vector_id or ""

    if target_type == TargetType.FEEDING.value:
        return postprocess_feeding_result(
            ir,
            full_events=full_events,
            user_input=user_input,
            device_no=device_no,
            model_config=model_config,
            need_confirm=need_confirm,
            matched_vector_id=matched_vector_id,
        )

    # 查记录确认：话术由 Python 点出事件名（叶子或父），父仍是是/否不是选叶子
    if need_confirm and target_type == TargetType.HISTORY.value:
        return create_history_confirm_response(
            ir,
            full_events=full_events,
            user_input=user_input,
            device_no=device_no,
            model_config=model_config,
            match_source=str(match_source or ""),
        )

    response = _build_intent_response(intent_result)
    llm_response = st.response or ""
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
    initial_state = IntentState(
        user_input=request.text,
        device_no=request.device_no,
        llm_model=model_config,
        event_dictionary=leaf_events,
        event_dictionary_full=full_events,
        conversation_id=thread_id,
    )

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
    initial_state: IntentState,
    thread_id: str,
    full_events: list,
    model_config: Dict[str, Any],
) -> AsyncGenerator[str, None]:
    """
    冷启动流式：intent_graph.astream(custom+updates) 逐步 thinking，再组装 answer。

    非流式仍走 intent_graph.ainvoke（同一张图）。
    """
    final_state: Any = initial_state
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
            final_state = payload

    response = _response_from_final_state(
        final_state,
        full_events=full_events,
        user_input=initial_state.user_input,
        device_no=initial_state.device_no,
        model_config=model_config,
    )

    answer_event = IntentStreamResponse(
        type="answer",
        content=json.dumps(response.model_dump(), ensure_ascii=False),
    )
    yield f"data: {json.dumps(answer_event.model_dump(), ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"

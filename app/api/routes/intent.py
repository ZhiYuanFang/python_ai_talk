"""
意图分析路由

业务说明：
提供 /v1/analyze/intent 与 /v1/analyze/intent/stream。
主交互为同一输入框：可选 conversation_id 续聊 pending 澄清（父事件消歧 / 叶子确认）。
自由文本解析；答非所问清 pending 当新意图。父事件不可落库。

设计思路：
1. 缓存保留全量事件树，匹配使用叶子视图
2. 有 pending 时优先澄清解析
3. 精确父名命中强制消歧
4. 图执行后对 feeding 结果做叶子校验与 pending 改写
5. 不再使用 /intent/confirm 枚举确认通道
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.feeding.graphs.intent_graph import intent_graph
from app.feeding.graphs.nodes.thinking_messages import get_thinking_message
from app.feeding.schemas.intent import IntentRequest, IntentResponse, IntentStreamResponse
from app.feeding.services.event_cache import event_cache
from app.feeding.services.intent_pipeline import (
    build_intent_response_from_fields,
    postprocess_feeding_result,
    try_exact_parent_disambiguation,
    try_handle_pending,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyze", tags=["意图分析"])


def _run_config(thread_id: str) -> Dict[str, Any]:
    """构建 LangGraph RunnableConfig。"""
    return {"configurable": {"thread_id": thread_id}}


def _model_config_dict(request: IntentRequest) -> Dict[str, Any]:
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
    """冷启动意图流程：父名检测 → 图执行 → feeding 后处理。"""
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

    target_type = intent_result.get("target_type", "conversation")
    need_confirm = bool(final_state.get("need_confirm", False))
    matched_vector_id = final_state.get("matched_vector_id", "") or ""

    if target_type == "feeding":
        return postprocess_feeding_result(
            intent_result,
            full_events=full_events,
            user_input=user_input,
            device_no=device_no,
            model_config=model_config,
            need_confirm=need_confirm,
            matched_vector_id=matched_vector_id,
        )

    response = _build_intent_response(intent_result)
    if target_type in ("history", "suggest", "conversation"):
        llm_response = final_state.get("response", "")
        if llm_response:
            response.content = llm_response
    return response


@router.post("/intent", response_model=IntentResponse, summary="意图分析")
async def analyze_intent(request: IntentRequest):
    """
    意图分析接口（非流式）

    同一输入框续聊：可选 conversation_id；有 pending 则自由文本澄清，
    答非所问则当新意图。父事件命中强制消歧，只落叶子。
    """
    logger.info(
        f"意图分析请求: device_no={request.device_no}, text={request.text[:50]}..., "
        f"conversation_id={request.conversation_id}"
    )

    full_events, leaf_events = await _prepare_dictionaries()
    model_config = _model_config_dict(request)

    # pending 续聊
    if request.conversation_id:
        pending_resp, as_new = await try_handle_pending(
            request.text, request.conversation_id, full_events
        )
        if pending_resp is not None:
            return pending_resp
        # as_new 或 pending 不存在：继续冷启动

    response = await _run_cold_intent(
        text=request.text,
        device_no=request.device_no,
        model_config=model_config,
        full_events=full_events,
        leaf_events=leaf_events,
    )

    logger.info(
        f"意图分析结果: target_type={response.target_type}, "
        f"action={response.action}, event_id={response.event_id}, "
        f"need_confirm={response.need_confirm}, confirm_type={response.confirm_type}"
    )
    return response


@router.post("/intent/stream", summary="意图分析（流式）")
async def analyze_intent_stream(request: IntentRequest):
    """
    意图分析流式接口。

    pending 续聊与父消歧与非流式相同；冷启动时推送节点 thinking。
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
    """冷启动流式执行图并推送 thinking / answer。"""
    final_state: Dict[str, Any] = dict(initial_state)
    run_config = _run_config(thread_id)

    async for chunk in intent_graph.astream(
        initial_state, config=run_config, stream_mode="updates"
    ):
        updates_map: Dict[str, Any] = {}
        if isinstance(chunk, tuple) and len(chunk) >= 2:
            second = chunk[1]
            if isinstance(second, dict):
                updates_map = second
        elif isinstance(chunk, dict):
            updates_map = chunk

        for node_name, node_update in updates_map.items():
            thinking_text = get_thinking_message(node_name)
            event = IntentStreamResponse(
                type="thinking",
                content=thinking_text,
                node=node_name,
            )
            yield f"data: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n"
            if isinstance(node_update, dict):
                final_state.update(node_update)

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

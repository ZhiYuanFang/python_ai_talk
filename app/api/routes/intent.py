"""
意图分析路由

业务说明：
提供 /v1/analyze/intent 与 /v1/analyze/intent/stream，同一套意图图与后处理。
非流式不再伪装 clinic。陪伴走 /v1/clinic。
"""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.feeding.graphs.intent_graph import intent_graph
from app.feeding.graphs.states.intent_state import IntentState
from app.feeding.schemas.intent import IntentRequest, IntentResponse, IntentStreamResponse
from app.feeding.schemas.intent_result import coerce_intent_result
from app.feeding.services.clarification import clarification_store
from app.feeding.services.event_cache import event_cache
from app.feeding.services.agent_miss_record import (
    infer_miss_fail_kind,
    maybe_record_agent_miss,
)
from app.feeding.services.agent_miss_soft_reply import soft_reply_for_miss
from app.feeding.services.intent_pipeline import (
    build_intent_response_from_fields,
    create_history_confirm_response,
    create_predict_confirm_response,
    postprocess_feeding_result,
    response_from_pending,
    try_exact_parent_disambiguation,
    try_handle_pending,
)
from app.shared.constants import TargetType
from app.shared.graphs.node_thinking import ensure_orchestration_thinking_content
from app.shared.graphs.state_patch import ensure_model
from app.shared.graphs.stream_graph import iter_graph_custom_thinking

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyze", tags=["意图分析"])


async def _finish_intent_response(
    response: IntentResponse,
    *,
    user_input: str,
    device_no: str,
    model_config: Optional[Dict[str, Any]] = None,
) -> IntentResponse:
    """
    对外返回前：终局 miss 先硬文案落库，再 LLM 软回复替换 content。

    确认/消歧也记下对外句子。软回复失败回退硬文案。硬文案留在 miss_canonical_content。
    近况在软回复之前读取，本函数返回前再写入本轮听到的句子。
    """
    from app.feeding.services.intent_recent_talk import intent_recent_talk_store

    hard = str(response.content or "")
    need_confirm = bool(response.need_confirm)
    confirm_type = str(getattr(response, "confirm_type", None) or "").strip()
    options = list(response.options or [])
    spoken = ""
    try:
        # 确认中不润色，但确认句本身要留给下一轮近况
        if need_confirm or confirm_type or options:
            spoken = str(getattr(response, "confirm_message", None) or hard).strip()
            return response

        kind = infer_miss_fail_kind(
            content=hard,
            target_type=str(response.target_type or ""),
            need_confirm=False,
        )
        if not kind:
            spoken = hard.strip()
            return response

        try:
            maybe_record_agent_miss(
                {
                    "content": hard,
                    "target_type": response.target_type or "",
                    "need_confirm": False,
                    "confirm_type": "",
                    "options": [],
                    "conversation_id": getattr(response, "conversation_id", None) or "",
                    "utterance": user_input,
                },
                user_input=user_input,
                device_no=device_no,
                conversation_id=str(
                    getattr(response, "conversation_id", None) or ""
                ),
            )
        except Exception as exc:
            logger.warning("覆盖缺口挂钩失败: %s", exc)

        response.miss_canonical_content = hard
        response.miss_fail_kind = kind
        try:
            soft = await soft_reply_for_miss(
                utterance=user_input,
                hard_content=hard,
                fail_kind=kind,
                device_no=device_no,
                llm_model=model_config,
            )
            if soft:
                response.content = soft
        except Exception as exc:
            logger.warning("miss 软回复失败，保留硬文案: %s", exc)
        spoken = str(response.content or "").strip()
        return response
    finally:
        try:
            await intent_recent_talk_store.append_turn(
                device_no,
                user=user_input,
                assistant=spoken,
            )
        except Exception as exc:
            logger.warning("记录意图近况失败: %s", exc)


def _run_config(thread_id: str) -> Dict[str, Any]:
    """构建 LangGraph RunnableConfig。"""
    return {"configurable": {"thread_id": thread_id}}


def _model_config_dict(request: IntentRequest) -> Dict[str, Any]:
    """
    从请求取出 Go 传入的 model（写入 state/日志）。

    业务说明：
    路由不再本地写死型号；TEMPORARY 实际上游选型由 llm_client 硬编码覆盖。
    """
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
    return await _response_from_final_state(
        final_state,
        full_events=full_events,
        user_input=text,
        device_no=device_no,
        model_config=model_config,
    )


async def _response_from_final_state(
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
        return await _finish_intent_response(
            _build_intent_response(intent_result),
            user_input=user_input,
            device_no=device_no,
            model_config=model_config,
        )

    # 零命中无法识别：other 短回复，不进确认
    tt0 = str(intent_result.get("target_type") or "")
    if tt0 in (
        TargetType.CONVERSATION.value,
        TargetType.OTHER.value,
    ) and (intent_result.get("content") or "").startswith("无法识别对应的事件"):
        return await _finish_intent_response(
            _build_intent_response(intent_result),
            user_input=user_input,
            device_no=device_no,
            model_config=model_config,
        )

    target_type = intent_result.get("target_type", TargetType.OTHER.value)
    read_source = str(intent_result.get("read_source") or "").strip().lower()
    need_confirm = bool(st.need_confirm)
    matched_vector_id = st.matched_vector_id or ""

    # C/U/D（含遗留 feeding）走喂养后处理
    if target_type in (
        TargetType.FEEDING.value,
        TargetType.CREATE.value,
        TargetType.UPDATE.value,
        TargetType.DELETE.value,
    ):
        return await _finish_intent_response(
            postprocess_feeding_result(
                ir,
                full_events=full_events,
                user_input=user_input,
                device_no=device_no,
                model_config=model_config,
                need_confirm=need_confirm,
                matched_vector_id=matched_vector_id,
            ),
            user_input=user_input,
            device_no=device_no,
            model_config=model_config,
        )

    # 查记录确认：R·record（含遗留 history）
    if need_confirm and (
        target_type == TargetType.HISTORY.value
        or (target_type == TargetType.READ.value and read_source != "predict")
    ):
        return await _finish_intent_response(
            create_history_confirm_response(
                ir,
                full_events=full_events,
                user_input=user_input,
                device_no=device_no,
                model_config=model_config,
                match_source=str(match_source or ""),
            ),
            user_input=user_input,
            device_no=device_no,
            model_config=model_config,
        )

    # 预测问答确认：R·predict（含遗留 predict）
    if need_confirm and (
        target_type == TargetType.PREDICT.value
        or (target_type == TargetType.READ.value and read_source == "predict")
    ):
        return await _finish_intent_response(
            create_predict_confirm_response(
                ir,
                full_events=full_events,
                user_input=user_input,
                device_no=device_no,
                model_config=model_config,
                match_source=str(match_source or ""),
            ),
            user_input=user_input,
            device_no=device_no,
            model_config=model_config,
        )

    response = _build_intent_response(intent_result)
    llm_response = st.response or ""
    if llm_response and not response.content:
        response.content = llm_response
    return await _finish_intent_response(
        response,
        user_input=user_input,
        device_no=device_no,
        model_config=model_config,
    )


def _sse_headers() -> Dict[str, str]:
    """SSE 响应头。"""
    return {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }


async def _run_one_sync_attempt(
    *,
    text: str,
    device_no: str,
    conversation_id: Optional[str],
    model_config: Dict[str, Any],
    full_events: list,
    leaf_events: list,
) -> IntentResponse:
    """
    单次同步意图尝试：pending 续聊或冷启动。

    答非所问（as_new）时同请求内继续冷启动。
    """
    if conversation_id:
        pending_resp, _as_new = await try_handle_pending(
            text, conversation_id, full_events
        )
        if pending_resp is not None:
            return pending_resp
        # pending 不存在或答非所问：继续冷启动
    return await _run_cold_intent(
        text=text,
        device_no=device_no,
        model_config=model_config,
        full_events=full_events,
        leaf_events=leaf_events,
    )


@router.post("/intent", response_model=IntentResponse, summary="意图分析")
async def analyze_intent(request: IntentRequest):
    """
    非流式意图分析：与 stream 同一套 pending / 图 / 后处理。

    每句直接进图，不按设备占坑或挂起。
    """
    logger.info(
        f"非流式意图: device_no={request.device_no}, "
        f"text={request.text[:50]}..., conversation_id={request.conversation_id}"
    )
    full_events, leaf_events = await _prepare_dictionaries()
    model_config = _model_config_dict(request)
    try:
        return await _run_one_sync_attempt(
            text=request.text,
            device_no=request.device_no,
            conversation_id=request.conversation_id,
            model_config=model_config,
            full_events=full_events,
            leaf_events=leaf_events,
        )
    except Exception as exc:
        logger.exception("非流式意图异常 device=%s: %s", request.device_no, exc)
        raise


@router.post("/intent/stream", summary="意图分析（流式）")
async def analyze_intent_stream(request: IntentRequest):
    """
    意图分析流式接口。

    每句推送本轮 thinking 与终答，不因同设备已有请求而挂起。
    """
    logger.info(
        f"意图分析流式请求: device_no={request.device_no}, text={request.text[:50]}..., "
        f"conversation_id={request.conversation_id}"
    )

    full_events, leaf_events = await _prepare_dictionaries()
    model_config = _model_config_dict(request)
    return StreamingResponse(
        _stream_intent(
            text=request.text,
            device_no=request.device_no,
            conversation_id=request.conversation_id,
            full_events=full_events,
            leaf_events=leaf_events,
            model_config=model_config,
        ),
        media_type="text/event-stream",
        headers=_sse_headers(),
    )


async def _stream_answer_done(response: IntentResponse) -> AsyncGenerator[str, None]:
    """推送一条 answer 与 [DONE]。"""
    answer_event = IntentStreamResponse(
        type="answer",
        content=json.dumps(response.model_dump(), ensure_ascii=False),
    )
    yield f"data: {json.dumps(answer_event.model_dump(), ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"


async def _stream_intent(
    *,
    text: str,
    device_no: str,
    conversation_id: Optional[str],
    full_events: list,
    leaf_events: list,
    model_config: Dict[str, Any],
) -> AsyncGenerator[str, None]:
    """
    推送本句 thinking 与终答。

    有 conversation_id 时先走续聊；否则冷启动。不拼接同设备的另一句。
    """
    try:
        response: Optional[IntentResponse] = None
        if conversation_id and clarification_store.get(conversation_id):
            async for kind, payload in _iter_pending_stream(
                text=text,
                conversation_id=conversation_id,
                full_events=full_events,
            ):
                if kind == "thinking":
                    event = IntentStreamResponse(
                        type="thinking",
                        content=str(payload),
                        node="pending_clarify",
                    )
                    yield (
                        f"data: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n"
                    )
                elif kind == "result":
                    pending_resp, as_new = payload
                    if pending_resp is not None:
                        response = pending_resp
                    elif as_new:
                        async for chunk, resp in _iter_cold_thinking(
                            text=text,
                            device_no=device_no,
                            full_events=full_events,
                            leaf_events=leaf_events,
                            model_config=model_config,
                        ):
                            if chunk:
                                yield chunk
                            if resp is not None:
                                response = resp
                    else:
                        response = IntentResponse(
                            target_type="other",
                            content="",
                            need_confirm=False,
                        )
        else:
            async for chunk, resp in _iter_cold_thinking(
                text=text,
                device_no=device_no,
                full_events=full_events,
                leaf_events=leaf_events,
                model_config=model_config,
            ):
                if chunk:
                    yield chunk
                if resp is not None:
                    response = resp

        if response is None:
            response = IntentResponse(
                target_type="other",
                content="脑电波过载，请稍后重试",
                need_confirm=False,
            )
        async for chunk in _stream_answer_done(response):
            yield chunk
    except Exception as exc:
        logger.exception("流式意图异常 device=%s: %s", device_no, exc)
        err = IntentResponse(
            target_type="other",
            content="脑电波过载，请稍后重试",
            need_confirm=False,
        )
        async for chunk in _stream_answer_done(err):
            yield chunk


async def _iter_pending_stream(
    *,
    text: str,
    conversation_id: str,
    full_events: list,
) -> AsyncGenerator[tuple, None]:
    """
    pending 澄清：边推 thinking 边跑；结束 yield ("result", (resp, as_new))。
    """
    queue: asyncio.Queue = asyncio.Queue()
    first_llm_thinking = True

    async def on_thinking(delta: str) -> None:
        nonlocal first_llm_thinking
        piece = delta if delta is not None else ""
        if not piece:
            return
        if first_llm_thinking:
            piece = ensure_orchestration_thinking_content(piece)
            first_llm_thinking = False
        await queue.put(("thinking", piece))

    async def _run_pending() -> None:
        try:
            resp, as_new = await try_handle_pending(
                text,
                conversation_id,
                full_events,
                on_thinking=on_thinking,
            )
            await queue.put(("result", (resp, as_new)))
        except Exception as e:
            await queue.put(("error", e))

    task = asyncio.create_task(_run_pending())
    try:
        while True:
            kind, payload = await queue.get()
            if kind == "thinking":
                yield ("thinking", payload)
            elif kind == "result":
                yield ("result", payload)
                return
            elif kind == "error":
                raise payload
    finally:
        await task


async def _iter_cold_thinking(
    *,
    text: str,
    device_no: str,
    full_events: list,
    leaf_events: list,
    model_config: Dict[str, Any],
) -> AsyncGenerator[tuple, None]:
    """
    冷启动仅推 thinking；最后一次 yield (None, IntentResponse)。

    精确父名短路无 thinking，直接 (None, resp)。
    """
    parent_resp = try_exact_parent_disambiguation(
        text,
        full_events,
        device_no=device_no,
        model_config=model_config,
    )
    if parent_resp is not None:
        yield (None, parent_resp)
        return

    thread_id = str(uuid4())
    initial_state = IntentState(
        user_input=text,
        device_no=device_no,
        llm_model=model_config,
        event_dictionary=leaf_events,
        event_dictionary_full=full_events,
        conversation_id=thread_id,
    )
    final_state: Any = initial_state
    async for kind, payload in iter_graph_custom_thinking(
        intent_graph, initial_state
    ):
        if kind == "thinking":
            event = IntentStreamResponse(
                type="thinking",
                content=str(payload.get("content") or ""),
                node=str(payload.get("node") or "") or None,
            )
            yield (
                f"data: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n",
                None,
            )
        elif kind == "final":
            final_state = payload

    response = await _response_from_final_state(
        final_state,
        full_events=full_events,
        user_input=text,
        device_no=device_no,
        model_config=model_config,
    )
    yield (None, response)

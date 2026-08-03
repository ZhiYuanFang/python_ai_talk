"""
调用诊疗 Agent 节点

业务说明：
当意图为 history / conversation / suggest 时，同进程走 clinic 数据准备 + 闺蜜生成，
并与 tip/clinic 共享 companion session（读 chat_context、写轮次）。
隐式飞轮由 clinic_graph 入口节点执行。
history 设 skip_knowledge + force_needs_history。
流式编排下对 clinic_graph astream 并转发 custom thinking；非流式 ainvoke。
"""

import logging
import uuid
from typing import Any, Dict

from app.clinic.graphs.clinic_graph import clinic_graph
from app.clinic.graphs.nodes.generate_clinic_answer import generate_clinic_answer
from app.shared.baby_age import age_band_from_months
from app.shared.companion_session import (
    companion_session_store,
    extract_knowledge_ids,
    format_chat_turns_for_prompt,
)
from app.shared.constants import IntentAction, TargetType
from app.shared.graphs.node_thinking import is_graph_streaming
from app.shared.graphs.stream_graph import ainvoke_or_astream_forward

logger = logging.getLogger(__name__)

CLINIC_FALLBACK = "抱歉，我暂时无法回答您的问题，请稍后再试。"


def _build_preserved_result(
    intent_result: Any,
    content: str,
    *,
    ensure_target: bool = False,
) -> Dict[str, Any]:
    """保留原 target_type，写入 content/action。"""
    preserved = dict(intent_result) if isinstance(intent_result, dict) else {}
    preserved["action"] = preserved.get("action") or IntentAction.REPLY.value
    preserved["content"] = content
    if ensure_target and not preserved.get("target_type"):
        preserved["target_type"] = TargetType.CONVERSATION.value
    return preserved


async def call_clinic_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    调用诊疗 Agent：读会话 → clinic_graph 数据准备（含飞轮）→ 闺蜜生成 → 写会话。

    Returns:
        更新 intent_result 与 response；写会话失败不影响返回值。
    """
    user_input = state.get("user_input", "")
    device_no = state.get("device_no", "")
    model_config = state.get("model_config", {}) or {}
    intent_result = state.get("intent_result", {})
    event_dictionary = state.get("event_dictionary")
    if not event_dictionary:
        from app.feeding.services.event_cache import event_cache

        event_dictionary = await event_cache.get_event_dictionary()

    logger.info(
        f"开始调用诊疗 Agent，device_no={device_no}, user_input={user_input[:50]}"
    )

    # 读陪伴会话 → chat_context（飞轮在 clinic_graph 内）
    chat_context = ""
    try:
        session = await companion_session_store.get(device_no)
        chat_context = format_chat_turns_for_prompt(session.turns)
    except Exception as e:
        logger.warning(f"读取陪伴会话失败，继续无 chat_context: {e}")

    target_type = ""
    if isinstance(intent_result, dict):
        target_type = str(intent_result.get("target_type") or "")
    is_history = target_type == TargetType.HISTORY.value
    skip_knowledge = is_history
    force_needs_history = is_history

    clinic_state = {
        "question": user_input,
        "device_no": device_no,
        "model_config": model_config,
        "event_dictionary": event_dictionary or [],
        "chat_context": chat_context,
        "skip_knowledge": skip_knowledge,
        "force_needs_history": force_needs_history,
    }
    if skip_knowledge:
        logger.info("history 意图：clinic 数据准备跳过 search_vectors，强制拉取历史")

    try:
        # 数据准备：流式转发 custom；非流式 ainvoke
        clinic_result = await ainvoke_or_astream_forward(
            clinic_graph,
            clinic_state,
            forward_custom=is_graph_streaming(),
        )
        merged_state: Dict[str, Any] = dict(clinic_result)
        merged_state["question"] = user_input
        merged_state["user_input"] = user_input
        merged_state["chat_context"] = chat_context
        merged_state["model_config"] = model_config
        if skip_knowledge:
            merged_state["knowledge"] = []

        used_fallback = False
        if merged_state.get("qa_hit") and str(merged_state.get("qa_answer") or "").strip():
            clinic_response = str(merged_state.get("qa_answer") or "").strip()
            logger.info(
                "诊疗 Agent 走 Q&A 捷径: id=%s, sim=%s",
                merged_state.get("qa_match_id"),
                merged_state.get("qa_match_score"),
            )
        else:
            generate_result = await generate_clinic_answer(merged_state)
            clinic_response = (generate_result.get("response") or "").strip()
            if not clinic_response:
                logger.warning("诊疗 Agent 闺蜜生成返回为空，使用兜底文案")
                clinic_response = CLINIC_FALLBACK
                used_fallback = True

        logger.info(f"诊疗 Agent 调用成功，response={clinic_response[:50]}")

        if not used_fallback and clinic_response != CLINIC_FALLBACK:
            knowledge_ids = extract_knowledge_ids(merged_state.get("knowledge"))
            answer_id = f"intent_{uuid.uuid4().hex[:12]}"
            age_band = merged_state.get("age_band") or age_band_from_months(
                merged_state.get("baby_age_months")
            )
            try:
                await companion_session_store.append_turn(
                    device_no,
                    user=user_input,
                    assistant=clinic_response,
                    source="intent",
                    answer_id=answer_id,
                    knowledge_ids=knowledge_ids,
                    suggestion_text=clinic_response,
                    standalone_question=merged_state.get("standalone_question") or "",
                    age_band=age_band or "",
                )
            except Exception as e:
                logger.warning(f"写入陪伴会话失败（不中断意图响应）: {e}")

        preserved = _build_preserved_result(intent_result, clinic_response)
        return {
            "intent_result": preserved,
            "response": clinic_response,
        }

    except Exception as e:
        logger.error(f"诊疗 Agent 调用失败: {str(e)}", exc_info=True)
        preserved = _build_preserved_result(
            intent_result, CLINIC_FALLBACK, ensure_target=True
        )
        return {
            "intent_result": preserved,
            "response": CLINIC_FALLBACK,
        }

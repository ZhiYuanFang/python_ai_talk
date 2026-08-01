"""
调用诊疗 Agent 节点

业务说明：
当意图为 conversation / suggest 时，同进程走 clinic 数据准备 + 闺蜜生成，
并与 tip/clinic 共享 companion session（读 chat_context、写轮次、隐式飞轮）。

流程：
1. 隐式飞轮（对 last_suggestion）
2. 读会话注入 chat_context
3. clinic_graph.ainvoke 数据准备
4. generate_clinic_answer（clinic_answer + invoke）
5. 成功非兜底则 append_turn(source=intent) + last_suggestion

失败时返回兜底文案且不写会话，保证意图始终有响应。
"""

import logging
import uuid
from typing import Any, Dict

from app.clinic.graphs.clinic_graph import clinic_graph
from app.clinic.graphs.nodes.generate_clinic_answer import generate_clinic_answer
from app.shared.companion_session import (
    companion_session_store,
    extract_knowledge_ids,
    format_chat_turns_for_prompt,
)
from app.shared.constants import IntentAction, TargetType
from app.shared.suggestion_acceptance import maybe_apply_implicit_feedback

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
    调用诊疗 Agent：飞轮 → 读会话 → 数据准备 → 闺蜜生成 → 写会话。

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

    # 1. 隐式飞轮（失败不阻断）
    try:
        await maybe_apply_implicit_feedback(device_no, user_input, model_config)
    except Exception as e:
        logger.error(f"隐式飞轮异常（不中断主流程）: {e}", exc_info=True)

    # 2. 读陪伴会话 → chat_context
    chat_context = ""
    try:
        session = await companion_session_store.get(device_no)
        chat_context = format_chat_turns_for_prompt(session.turns)
    except Exception as e:
        logger.warning(f"读取陪伴会话失败，继续无 chat_context: {e}")

    clinic_state = {
        "question": user_input,
        "device_no": device_no,
        "model_config": model_config,
        "event_dictionary": event_dictionary or [],
        "chat_context": chat_context,
    }

    try:
        # 3. 数据准备
        clinic_result = await clinic_graph.ainvoke(clinic_state)
        merged_state: Dict[str, Any] = dict(clinic_result)
        merged_state["question"] = user_input
        merged_state["user_input"] = user_input
        merged_state["chat_context"] = chat_context
        merged_state["model_config"] = model_config

        # 4. 闺蜜同步生成（不再走 generate_response）
        generate_result = await generate_clinic_answer(merged_state)
        clinic_response = (generate_result.get("response") or "").strip()

        used_fallback = False
        if not clinic_response:
            logger.warning("诊疗 Agent 闺蜜生成返回为空，使用兜底文案")
            clinic_response = CLINIC_FALLBACK
            used_fallback = True

        logger.info(f"诊疗 Agent 调用成功，response={clinic_response[:50]}")

        # 5. 成功非兜底：写共享会话
        if not used_fallback and clinic_response != CLINIC_FALLBACK:
            knowledge_ids = extract_knowledge_ids(merged_state.get("knowledge"))
            answer_id = f"intent_{uuid.uuid4().hex[:12]}"
            try:
                await companion_session_store.append_turn(
                    device_no,
                    user=user_input,
                    assistant=clinic_response,
                    source="intent",
                    answer_id=answer_id,
                    knowledge_ids=knowledge_ids,
                    suggestion_text=clinic_response,
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

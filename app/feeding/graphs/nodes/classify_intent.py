"""
意图分类节点

业务说明：
使用 LLM 对用户输入进行意图分类。
产出以 events[].op 为权威；无顶层 op/action。
分类路径默认先确认，免确认只留给意图缓存命中。
"""

import json
import logging
from typing import Any, Dict

from app.feeding.graphs.nodes.prompts.intent_classification import (
    build_intent_classification_system_prompt,
    build_intent_classification_user_message,
)
from app.feeding.schemas.intent_result import IntentResult, coerce_intent_result
from app.feeding.services.event_name_match import match_feeding_event
from app.feeding.services.intent_events import (
    first_display_event,
    has_cud_events,
    has_read_events,
    normalize_intent_events,
)
from app.feeding.utils.quantity_extractor import extract_quantity_from_text
from app.shared.constants import (
    LLM_OVERLOAD_RETRY_MESSAGE,
    MatchSource,
    TargetType,
)
from app.shared.graphs.node_thinking import emit_thinking
from app.shared.graphs.state_patch import state_get
from app.shared.llm_client import llm_client, llm_model_config_from_mapping
from app.shared.llm_json import loads_llm_json

logger = logging.getLogger(__name__)


def _parse_intent_result(content: str) -> Dict[str, Any]:
    """解析 LLM 返回的意图 JSON；失败则软回 conversation。"""
    try:
        result = loads_llm_json(content)
        if not isinstance(result, dict):
            raise ValueError("意图 JSON 顶层须为对象")
        logger.info(f"LLM 意图解析成功: {json.dumps(result, ensure_ascii=False)}")
        return result
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.error(f"LLM 返回内容 JSON 解析失败: {e}, content={content[:200]}")
        return {
            "target_type": TargetType.CONVERSATION.value,
            "events": [],
            "keywords": [],
            "content": content,
        }


async def classify_intent(state: Any) -> Dict[str, Any]:
    """
    意图分类节点。

    归一 events 子项 op；feeding/history 无有效事件时降为 conversation 软提示。
    """
    text = state_get(state, "user_input") or state_get(state, "text", "")
    event_dictionary = (
        state_get(state, "event_dictionary_full")
        or state_get(state, "event_dictionary")
        or []
    )
    device_no = state_get(state, "device_no", "")

    llm_model = (
        state_get(state, "llm_model")
        or state_get(state, "model_config")
        or state_get(state, "model")
        or {}
    )
    llm_model_config = llm_model_config_from_mapping(llm_model)

    logger.info(
        "开始意图分类: device_no=%s, text=%s..., model=%s/%s",
        device_no,
        text[:20],
        (llm_model_config.provider if llm_model_config else "(missing)"),
        (llm_model_config.name if llm_model_config else "-"),
    )

    try:
        system_prompt = build_intent_classification_system_prompt(
            event_dictionary,
            in_progress_hint=str(state_get(state, "in_progress_hint") or ""),
        )
        user_message = build_intent_classification_user_message(text)

        response = await llm_client.invoke(
            messages=[{"role": "user", "content": user_message}],
            model_config=llm_model_config,
            system_prompt=system_prompt,
        )

        intent_result = _parse_intent_result(response.content)

        # 数量：优先沿用 state 已有，否则本地提取
        vector_quantity = None
        prior_ir = coerce_intent_result(state_get(state, "intent_result"))
        if prior_ir.quantity is not None:
            vector_quantity = prior_ir.quantity
        if vector_quantity is not None:
            intent_result["quantity"] = vector_quantity
        elif intent_result.get("quantity") is None:
            extracted_quantity = extract_quantity_from_text(text)
            if extracted_quantity is not None:
                intent_result["quantity"] = extracted_quantity

        intent_result.setdefault("target_type", TargetType.CONVERSATION.value)
        intent_result.setdefault("event_name", "")
        intent_result.setdefault("event_id", "")
        intent_result.setdefault("quantity", None)
        intent_result["event_type"] = None
        intent_result.setdefault("event_unit", None)
        intent_result.setdefault("is_new_event", False)
        intent_result.setdefault(
            "remark_keyword", state_get(state, "remark_keyword") or ""
        )
        intent_result.setdefault("event_ids", [])
        intent_result.setdefault("missing_events", [])
        intent_result.setdefault("match_source", MatchSource.LLM.value)
        intent_result.setdefault("match_confidence", 1.0)
        intent_result.setdefault("keywords", [])
        intent_result.setdefault("content", "")
        intent_result.setdefault("events", [])

        # 子项字典匹配
        if intent_result.get("events"):
            for event in intent_result["events"]:
                if not isinstance(event, dict):
                    continue
                event.pop("event_type", None)
                if event.get("event_name") and not event.get("event_id"):
                    matched = match_feeding_event(
                        event["event_name"], event_dictionary
                    )
                    if matched:
                        event["event_id"] = matched["event_id"]
                        event["event_name"] = matched.get("event_name") or event[
                            "event_name"
                        ]
                    else:
                        event["event_id"] = ""
                if event.get("quantity") is None and intent_result.get("quantity") is not None:
                    event["quantity"] = intent_result["quantity"]
                elif event.get("quantity") is None:
                    eq = extract_quantity_from_text(text)
                    if eq is not None:
                        event["quantity"] = eq

        # 旧顶层单事件字段也做一次名称匹配，便于投影
        if intent_result.get("event_name") and not intent_result.get("event_id"):
            matched_event = match_feeding_event(
                intent_result["event_name"], event_dictionary
            )
            if matched_event:
                intent_result["event_id"] = matched_event["event_id"]
                intent_result["event_name"] = matched_event.get("event_name") or intent_result[
                    "event_name"
                ]

        intent_result = normalize_intent_events(intent_result, event_dictionary)

        # 展示字段取自首项
        head = first_display_event(intent_result)
        if head:
            intent_result["event_id"] = str(head.get("event_id") or intent_result.get("event_id") or "")
            intent_result["event_name"] = str(
                head.get("event_name") or intent_result.get("event_name") or ""
            )
            if head.get("quantity") is not None:
                intent_result["quantity"] = head.get("quantity")

        target = str(intent_result.get("target_type") or "").strip().lower()
        # feeding/history 必须有对应子项，否则降为 conversation
        if target == TargetType.FEEDING.value and not has_cud_events(intent_result):
            logger.warning("feeding 无 CUD 子项，降为 conversation")
            intent_result["target_type"] = TargetType.CONVERSATION.value
            intent_result["content"] = intent_result.get("content") or "请说明要记录或修改的具体事件。"
            intent_result["events"] = []
            target = TargetType.CONVERSATION.value
        if target == TargetType.HISTORY.value and not has_read_events(intent_result):
            logger.warning("history 无 read 子项，降为 conversation")
            intent_result["target_type"] = TargetType.CONVERSATION.value
            intent_result["content"] = intent_result.get("content") or "请说明要查询的事件。"
            intent_result["events"] = []
            target = TargetType.CONVERSATION.value

        if target in (TargetType.CONVERSATION.value, TargetType.EXIT.value):
            need_confirm = False
            intent_result["events"] = []
        elif has_cud_events(intent_result) or has_read_events(intent_result):
            need_confirm = True
        else:
            need_confirm = True

        ops = [str(e.get("op") or "") for e in (intent_result.get("events") or []) if isinstance(e, dict)]
        logger.info(
            "意图分类完成: target_type=%s, events_ops=%s, event_name=%s, "
            "event_id=%s, need_confirm=%s",
            intent_result.get("target_type"),
            ops,
            intent_result.get("event_name"),
            intent_result.get("event_id"),
            need_confirm,
        )

        return {
            "intent_result": IntentResult.model_validate(intent_result),
            "match_confidence": 1.0,
            "match_source": MatchSource.LLM.value,
            "need_confirm": need_confirm,
            "confirm_message": intent_result.get("confirm_message") or "",
        }

    except Exception as e:
        logger.error(f"意图分类失败: {e}", exc_info=True)
        emit_thinking("classify_intent", LLM_OVERLOAD_RETRY_MESSAGE)
        return {
            "intent_result": IntentResult(
                target_type=TargetType.CONVERSATION.value,
                event_name="",
                event_id="",
                quantity=None,
                event_type=None,
                event_unit=None,
                is_new_event=False,
                match_source=MatchSource.LLM.value,
                match_confidence=0.0,
                keywords=[],
                content=LLM_OVERLOAD_RETRY_MESSAGE,
                events=[],
            ),
            "match_confidence": 0.0,
            "match_source": MatchSource.LLM.value,
        }

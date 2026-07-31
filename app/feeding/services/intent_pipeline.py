"""
意图分析管线辅助

业务说明：
统一处理 pending 澄清、父事件消歧、叶子校验与飞轮写入。
主路径为同一 /intent 输入框 + conversation_id 自由文本续聊。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from app.feeding.schemas.intent import IntentEvent, IntentResponse
from app.feeding.services.clarification import (
    ResolveStatus,
    clarification_store,
    create_leaf_confirm_pending,
    create_parent_disambiguation_pending,
    leaf_intent_result,
    pending_to_response_fields,
    resolve_free_text,
    try_parent_hit_from_event_id,
)
from app.feeding.services.event_hierarchy import (
    find_parent_by_exact_name,
    get_children,
    get_event_by_id,
    is_parent_event,
)
from app.feeding.services.event_vector_store import event_vector_store
from app.shared.constants import (
    ConfirmType,
    IntentAction,
    MatchSource,
    TargetType,
)

logger = logging.getLogger(__name__)


def build_intent_response_from_fields(fields: Dict[str, Any]) -> IntentResponse:
    """从字段字典构建 IntentResponse。"""
    options_raw = fields.get("options") or []
    options: List[IntentEvent] = []
    for opt in options_raw:
        if isinstance(opt, IntentEvent):
            options.append(opt)
        elif isinstance(opt, dict):
            options.append(
                IntentEvent(
                    action=opt.get("action") or "",
                    event_name=opt.get("event_name") or "",
                    event_id=str(opt.get("event_id") or ""),
                    quantity=opt.get("quantity"),
                )
            )

    return IntentResponse(
        target_type=fields.get("target_type", TargetType.CONVERSATION.value),
        action=fields.get("action", IntentAction.REPLY.value),
        event_name=fields.get("event_name", "") or "",
        event_id=str(fields.get("event_id", "") or ""),
        quantity=fields.get("quantity"),
        event_type=fields.get("event_type"),
        event_unit=fields.get("event_unit"),
        is_new_event=fields.get("is_new_event", False),
        keywords=fields.get("keywords") or [],
        content=fields.get("content", "") or "",
        events=fields.get("events") or [],
        match_confidence=fields.get("match_confidence"),
        match_source=fields.get("match_source"),
        need_confirm=bool(fields.get("need_confirm", False)),
        confirm_type=fields.get("confirm_type"),
        confirm_message=fields.get("confirm_message"),
        conversation_id=fields.get("conversation_id"),
        options=options,
    )


def apply_flywheel_after_leaf_resolution(
    *,
    leaf: Dict[str, Any],
    original_utterance: str,
    action: str,
    match_source: str,
    matched_vector_id: str = "",
    write_user_expression: bool = False,
) -> None:
    """消歧/确认成功落到叶子后写入飞轮；父事件永不写入。"""
    event_id = str(leaf.get("event_id") or "")
    event_name = leaf.get("event_name") or ""
    if not event_id or not event_name:
        return

    utterance = (original_utterance or "").strip()
    if write_user_expression and utterance:
        event_vector_store.add_user_expression(
            event_id=event_id,
            event_name=event_name,
            expression=utterance,
            action=action or IntentAction.ONE.value,
        )
        logger.info(
            f"数据飞轮：落到叶子后写入用户表达 event_id={event_id}, "
            f"expression={utterance[:30]}..."
        )

    if match_source == MatchSource.VECTOR.value and matched_vector_id:
        event_vector_store.increment_success_count(matched_vector_id)
        logger.info(f"向量匹配确认，递增成功计数: vector_id={matched_vector_id}")

    event_vector_store.check_and_cleanup()


def response_from_pending(pending) -> IntentResponse:
    """pending 澄清响应。"""
    return build_intent_response_from_fields(pending_to_response_fields(pending))


async def try_handle_pending(
    text: str,
    conversation_id: str,
    full_events: List[Dict[str, Any]],
) -> Tuple[Optional[IntentResponse], bool]:
    """
    处理 pending 续聊。

    Returns:
        (response, continue_as_new_intent)
        - response 非空：直接返回给客户端
        - continue_as_new_intent=True：清 pending，本句当新意图
    """
    pending = clarification_store.get(conversation_id)
    if not pending:
        return None, False

    result = await resolve_free_text(text, pending, full_events=full_events)

    if result.status == ResolveStatus.RESOLVED and result.event:
        # quantity：LLM/解析结果非 None 时覆盖 pending
        quantity = (
            result.quantity if result.quantity is not None else pending.quantity
        )
        clarification_store.clear(conversation_id)
        leaf = get_event_by_id(result.event.get("event_id"), full_events) or result.event
        # 防御 / correct 到父：不允许落库，改消歧
        if is_parent_event(leaf.get("event_id"), full_events):
            children = get_children(leaf.get("event_id"), full_events)
            parent = get_event_by_id(leaf.get("event_id"), full_events) or leaf
            if children:
                new_pending = create_parent_disambiguation_pending(
                    parent=parent,
                    children=children,
                    original_utterance=pending.original_utterance,
                    action=pending.action,
                    quantity=quantity,
                    match_source=pending.match_source,
                    # correct 否定旧猜想：不把旧向量成功信号带入新 pending
                    matched_vector_id=(
                        ""
                        if result.skip_vector_success
                        else pending.matched_vector_id
                    ),
                    device_no=pending.device_no,
                    model_config=pending.model_config,
                    conversation_id=conversation_id,
                )
                return response_from_pending(new_pending), False
            return (
                build_intent_response_from_fields(
                    {
                        "target_type": TargetType.CONVERSATION.value,
                        "action": IntentAction.REPLY.value,
                        "content": "无法确定具体事件，请重新描述。",
                    }
                ),
                False,
            )

        # correct：写原话到正确叶子，且不对旧向量 success++
        # 其余：沿用原飞轮条件
        write_expr = (
            result.skip_vector_success
            or pending.kind == ConfirmType.PARENT_DISAMBIGUATION.value
            or pending.match_source == MatchSource.LLM.value
        )
        matched_vid = (
            "" if result.skip_vector_success else pending.matched_vector_id
        )
        apply_flywheel_after_leaf_resolution(
            leaf=leaf,
            original_utterance=pending.original_utterance,
            action=pending.action,
            match_source=pending.match_source,
            matched_vector_id=matched_vid,
            write_user_expression=write_expr,
        )
        fields = leaf_intent_result(
            leaf,
            action=pending.action,
            quantity=quantity,
            match_source=pending.match_source,
            match_confidence=1.0,
            original_utterance=pending.original_utterance,
        )
        return build_intent_response_from_fields(fields), False

    if result.status == ResolveStatus.ASK_AGAIN:
        # 更新 pending 选项（可能缩小）
        if result.options:
            pending.options = result.options
        if result.message:
            pending.clarify_message = result.message
        clarification_store.set(pending)
        return response_from_pending(pending), False

    if result.status == ResolveStatus.REJECT:
        clarification_store.clear(conversation_id)
        return (
            build_intent_response_from_fields(
                {
                    "target_type": TargetType.CONVERSATION.value,
                    "action": IntentAction.REPLY.value,
                    "content": "好的，已取消。请重新描述您要记录的事件。",
                }
            ),
            False,
        )

    # OFF_TOPIC / new_intent：清 pending，当新意图
    clarification_store.clear(conversation_id)
    logger.info(
        f"消歧答非所问，清 pending 当新意图: conversation_id={conversation_id}, "
        f"text={text[:40]}..."
    )
    return None, True


def try_exact_parent_disambiguation(
    text: str,
    full_events: List[Dict[str, Any]],
    *,
    device_no: str,
    model_config: Dict[str, Any],
) -> Optional[IntentResponse]:
    """用户文本精确命中父事件名 → 强制消歧。"""
    parent = find_parent_by_exact_name(text, full_events)
    if not parent:
        return None
    children = get_children(parent.get("event_id"), full_events)
    if not children:
        return None
    pending = create_parent_disambiguation_pending(
        parent=parent,
        children=children,
        original_utterance=text,
        action=IntentAction.ONE.value,
        match_source=MatchSource.NAME.value,
        device_no=device_no,
        model_config=model_config,
    )
    logger.info(
        f"父事件名命中，进入消歧: parent={parent.get('event_name')}, "
        f"children={len(children)}"
    )
    return response_from_pending(pending)


def postprocess_feeding_result(
    intent_result: Dict[str, Any],
    *,
    full_events: List[Dict[str, Any]],
    user_input: str,
    device_no: str,
    model_config: Dict[str, Any],
    need_confirm: bool = False,
    matched_vector_id: str = "",
) -> IntentResponse:
    """
    对图执行后的 feeding 结果做叶子校验与消歧改写。

    - 父事件 → 强制消歧 pending
    - 叶子且 need_confirm → leaf_confirm pending（自由文本）
    - 叶子且无需确认 → 直接返回最终结果
    """
    event_id = intent_result.get("event_id") or ""
    action = intent_result.get("action") or IntentAction.ONE.value
    quantity = intent_result.get("quantity")
    match_source = intent_result.get("match_source") or MatchSource.LLM.value
    match_confidence = intent_result.get("match_confidence")

    # 多事件：逐个校验，若含父则整体改消歧（取第一个父）
    if action == IntentAction.MULTI.value:
        events = intent_result.get("events") or []
        for ev in events:
            eid = ev.get("event_id") or ""
            if is_parent_event(eid, full_events):
                pending = try_parent_hit_from_event_id(
                    eid,
                    full_events,
                    original_utterance=user_input,
                    action=ev.get("action") or IntentAction.ONE.value,
                    quantity=ev.get("quantity"),
                    match_source=match_source,
                    matched_vector_id=matched_vector_id,
                    device_no=device_no,
                    model_config=model_config,
                )
                if pending:
                    return response_from_pending(pending)
        # 多事件全是叶子：软确认
        pending = create_leaf_confirm_pending(
            leaf={
                "event_id": events[0].get("event_id") if events else "",
                "event_name": events[0].get("event_name") if events else "",
                "extra_names": [],
            },
            original_utterance=user_input,
            action=IntentAction.MULTI.value,
            quantity=quantity,
            match_source=match_source,
            matched_vector_id=matched_vector_id,
            device_no=device_no,
            model_config=model_config,
        )
        # 多事件确认话术覆盖
        names = "、".join(
            (e.get("event_name") or "") for e in events if e.get("event_name")
        )
        pending.clarify_message = (
            f"您是要记录以下事件吗：{names}？请回复确认或取消。"
            if names
            else pending.clarify_message
        )
        clarification_store.set(pending)
        return response_from_pending(pending)

    # 父事件强制消歧
    if event_id and is_parent_event(event_id, full_events):
        pending = try_parent_hit_from_event_id(
            event_id,
            full_events,
            original_utterance=user_input,
            action=action,
            quantity=quantity,
            match_source=match_source,
            matched_vector_id=matched_vector_id,
            device_no=device_no,
            model_config=model_config,
        )
        if pending:
            logger.info(f"匹配结果为父事件，强制消歧: event_id={event_id}")
            return response_from_pending(pending)
        # 父事件但无子：拒绝落库
        return build_intent_response_from_fields(
            {
                "target_type": TargetType.CONVERSATION.value,
                "action": IntentAction.REPLY.value,
                "content": "该分类下没有可记录的具体事件，请说明具体事项。",
                "match_source": match_source,
            }
        )

    # 叶子：需要确认则 pending；否则直接返回
    leaf = get_event_by_id(event_id, full_events) or {
        "event_id": event_id,
        "event_name": intent_result.get("event_name") or "",
    }

    if need_confirm or match_source == MatchSource.LLM.value:
        # LLM 或中置信：自由文本软确认
        if event_id:
            pending = create_leaf_confirm_pending(
                leaf=leaf,
                original_utterance=user_input,
                action=action,
                quantity=quantity,
                match_source=match_source,
                matched_vector_id=matched_vector_id,
                device_no=device_no,
                model_config=model_config,
            )
            return response_from_pending(pending)

    fields = {
        **intent_result,
        "need_confirm": False,
        "confirm_type": None,
        "confirm_message": None,
        "options": [],
        "conversation_id": None,
    }
    return build_intent_response_from_fields(fields)

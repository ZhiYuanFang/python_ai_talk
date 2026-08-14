"""
意图分析管线辅助

业务说明：
统一处理 pending 澄清、父事件消歧、叶子校验与飞轮写入。
主路径为同一 /intent 输入框 + conversation_id 自由文本续聊。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

from app.feeding.schemas.intent import IntentEvent, IntentResponse
from app.feeding.schemas.intent_result import IntentResult, coerce_intent_result
from app.feeding.services.clarification import (
    ResolveStatus,
    build_multi_event_confirm_message,
    clarification_store,
    create_leaf_confirm_pending,
    create_parent_disambiguation_pending,
    leaf_intent_result,
    pending_to_response_fields,
    resolve_event_display_name,
    resolve_free_text,
    try_parent_hit_from_event_id,
)
from app.feeding.services.event_hierarchy import (
    find_parent_by_exact_name,
    get_children,
    get_event_by_id,
    is_parent_event,
)
from app.shared.constants import (
    IntentAction,
    IntentOp,
    MatchSource,
    TargetType,
)

logger = logging.getLogger(__name__)

IntentFields = Union[IntentResult, Mapping[str, Any], Dict[str, Any]]


def _intent_fields(intent: IntentFields) -> Dict[str, Any]:
    """管线入口：IntentResult 或 dict → 字段字典，保持 API 组装不变。"""
    return coerce_intent_result(intent).to_plain_dict()


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
        is_new_event=False,
        keywords=fields.get("keywords") or [],
        content=fields.get("content", "") or "",
        events=fields.get("events") or [],
        op=fields.get("op"),
        remark_keyword=fields.get("remark_keyword"),
        missing_events=fields.get("missing_events") or [],
        match_confidence=fields.get("match_confidence"),
        match_source=fields.get("match_source"),
        need_confirm=bool(fields.get("need_confirm", False)),
        confirm_type=fields.get("confirm_type"),
        confirm_message=fields.get("confirm_message"),
        conversation_id=fields.get("conversation_id"),
        options=options,
    )


def apply_flywheel_after_leaf_resolution(*_args: Any, **_kwargs: Any) -> None:
    """单事件飞轮已删除；保留空实现避免旧调用点报错。"""
    return


def response_from_pending(pending) -> IntentResponse:
    """pending 澄清响应。"""
    return build_intent_response_from_fields(pending_to_response_fields(pending))


def create_history_confirm_response(
    intent_result: IntentFields,
    *,
    full_events: List[Dict[str, Any]],
    user_input: str,
    device_no: str,
    model_config: Dict[str, Any],
    match_source: str = "",
) -> IntentResponse:
    """
    查记录软确认：话术必带字典事件名（叶子或父）。

    父事件此处仍是是/否，不进入选叶子消歧。
    """
    fields = _intent_fields(intent_result)
    event_ids = [
        str(x)
        for x in (fields.get("event_ids") or [])
        if x not in (None, "")
    ]
    event_id = str(fields.get("event_id") or "")
    if event_id and event_id not in event_ids:
        event_ids = [event_id] + event_ids
    event_name = resolve_event_display_name(
        event_id=event_id,
        event_name=str(fields.get("event_name") or ""),
        events=full_events,
        event_ids=event_ids,
    )
    pending = create_leaf_confirm_pending(
        leaf={
            "event_id": event_id or (event_ids[0] if event_ids else ""),
            "event_name": event_name,
            "extra_names": [],
        },
        original_utterance=user_input,
        action=IntentAction.SEARCH.value,
        match_source=str(match_source or fields.get("match_source") or ""),
        device_no=device_no,
        model_config=model_config,
        events=fields.get("events") or [],
        op="read",
        remark_keyword=fields.get("remark_keyword") or "",
        start_time=fields.get("start_time") or fields.get("startTime"),
        end_time=fields.get("end_time") or fields.get("endTime"),
        event_ids=event_ids,
    )
    return response_from_pending(pending)


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
        pending_op = (getattr(pending, "op", None) or "").strip().lower()
        if not pending_op and pending.action == IntentAction.SEARCH.value:
            pending_op = IntentOp.READ.value
        # 查父确认：带着父 id 去拉史，不得改成选叶子
        if (
            pending_op == IntentOp.READ.value
            and is_parent_event(leaf.get("event_id"), full_events)
        ):
            parent_id = str(leaf.get("event_id") or "")
            fields = {
                "target_type": TargetType.HISTORY.value,
                "action": IntentAction.SEARCH.value,
                "op": IntentOp.READ.value,
                "event_id": parent_id,
                "event_name": leaf.get("event_name") or "",
                "event_ids": getattr(pending, "event_ids", None) or [parent_id],
                "remark_keyword": getattr(pending, "remark_keyword", None) or "",
                "events": getattr(pending, "events", None) or [],
                "start_time": getattr(pending, "start_time", None),
                "end_time": getattr(pending, "end_time", None),
                "match_source": pending.match_source,
                "match_confidence": 1.0,
            }
            executed = await _execute_after_confirm(
                fields,
                device_no=pending.device_no,
                user_input=pending.original_utterance,
                full_events=full_events,
            )
            return build_intent_response_from_fields(executed), False
        # 记事件命中父：不允许落库，改消歧
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
        fields = leaf_intent_result(
            leaf,
            action=pending.action,
            quantity=quantity,
            match_source=pending.match_source,
            match_confidence=1.0,
            original_utterance=pending.original_utterance,
        )
        # 确认后走批量落库或查记录模板，不再写单事件飞轮
        extra_events = getattr(pending, "events", None) or []
        if extra_events:
            fields["events"] = extra_events
        fields["op"] = getattr(pending, "op", None) or fields.get("op")
        fields["remark_keyword"] = getattr(pending, "remark_keyword", None) or ""
        # 查记录确认后带上 unix 窗与原始 event_ids（父 id 不在此展开）
        if getattr(pending, "event_ids", None):
            fields["event_ids"] = pending.event_ids
        elif pending_op == IntentOp.READ.value:
            # 备注消歧选中叶子：用该叶子 id 拉史
            leaf_id = str(leaf.get("event_id") or "")
            fields["event_ids"] = [leaf_id] if leaf_id else []
            fields["target_type"] = TargetType.HISTORY.value
            fields["action"] = IntentAction.SEARCH.value
            fields["op"] = IntentOp.READ.value
        if getattr(pending, "start_time", None) is not None:
            fields["start_time"] = pending.start_time
        if getattr(pending, "end_time", None) is not None:
            fields["end_time"] = pending.end_time
        executed = await _execute_after_confirm(
            fields,
            device_no=pending.device_no,
            user_input=pending.original_utterance,
            full_events=full_events,
        )
        return build_intent_response_from_fields(executed), False

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
    intent_result: IntentFields,
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
    fields = _intent_fields(intent_result)
    event_id = fields.get("event_id") or ""
    action = fields.get("action") or IntentAction.ONE.value
    quantity = fields.get("quantity")
    match_source = fields.get("match_source") or MatchSource.LLM.value
    match_confidence = fields.get("match_confidence")

    # 多事件：逐个校验，若含父则整体改消歧（取第一个父）
    # 复合切换可能漏标 action=multi，events 长度>1 同样走多事件确认
    events = fields.get("events") or []
    if action == IntentAction.MULTI.value or len(events) > 1:
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
            events=events,
            op=fields.get("op") or "create",
        )
        # 多事件确认必须点出每件动作（结束/开始/记录），禁止只说「记录以下事件」
        multi_msg = build_multi_event_confirm_message(events)
        if multi_msg:
            pending.clarify_message = multi_msg
        pending.events = events  # type: ignore[attr-defined]
        pending.op = fields.get("op") or "create"  # type: ignore[attr-defined]
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
        "event_name": fields.get("event_name") or "",
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
                events=fields.get("events") or [],
                op=fields.get("op") or "",
                remark_keyword=fields.get("remark_keyword") or "",
                confirm_message=fields.get("confirm_message"),
            )
            return response_from_pending(pending)

    out_fields = {
        **fields,
        "need_confirm": False,
        "confirm_type": None,
        # 空串而非 None：避免确认后续聊 coerce_intent_result 校验失败
        "confirm_message": "",
        "options": [],
        "conversation_id": None,
    }
    return build_intent_response_from_fields(out_fields)


async def _execute_after_confirm(
    fields: Dict[str, Any],
    *,
    device_no: str,
    user_input: str,
    full_events: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """确认通过后执行 batch 或查记录模板。"""
    from app.feeding.graphs.nodes.execute_history_crud import execute_history_crud
    from app.feeding.graphs.nodes.speak_history import speak_history
    from app.feeding.services.history_crud import infer_op
    from app.shared.constants import IntentOp

    state = {
        "intent_result": fields,
        "device_no": device_no,
        "user_input": user_input,
        "event_dictionary_full": full_events,
        "event_dictionary": full_events,
        "need_confirm": False,
    }
    op = infer_op(fields)
    if op == IntentOp.READ.value or fields.get("target_type") == TargetType.HISTORY.value:
        out = await speak_history(state)
    elif op in (IntentOp.CREATE.value, IntentOp.UPDATE.value, IntentOp.DELETE.value):
        out = await execute_history_crud(state)
    else:
        return fields
    merged = dict(fields)
    out_ir = out.get("intent_result")
    if out_ir is not None:
        merged.update(coerce_intent_result(out_ir).to_plain_dict())
    if out.get("response"):
        merged["content"] = out["response"]
    return merged

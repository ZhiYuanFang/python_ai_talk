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
from app.shared.graphs.stream_llm_collect import ThinkingCallback
from app.feeding.services.closed_interval import apply_time_slots_to_events
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
    """从字段字典构建 IntentResponse（无顶层 op/action）。"""
    options_raw = fields.get("options") or []
    options: List[IntentEvent] = []
    for opt in options_raw:
        if isinstance(opt, IntentEvent):
            options.append(opt)
        elif isinstance(opt, dict):
            options.append(
                IntentEvent(
                    op=str(opt.get("op") or ""),
                    action=opt.get("action") or "",
                    event_name=opt.get("event_name") or "",
                    event_id=str(opt.get("event_id") or ""),
                    quantity=opt.get("quantity"),
                    remark=opt.get("remark"),
                    start_time=opt.get("start_time"),
                    end_time=opt.get("end_time"),
                )
            )

    events_raw = fields.get("events") or []
    events: List[IntentEvent] = []
    for ev in events_raw:
        if isinstance(ev, IntentEvent):
            events.append(ev)
        elif isinstance(ev, dict):
            events.append(
                IntentEvent(
                    op=str(ev.get("op") or ""),
                    action=ev.get("action") or "",
                    event_name=ev.get("event_name") or "",
                    event_id=str(ev.get("event_id") or ""),
                    quantity=ev.get("quantity"),
                    history_id=ev.get("history_id"),
                    remark=ev.get("remark"),
                    start_time=ev.get("start_time"),
                    end_time=ev.get("end_time"),
                )
            )

    # 非 R·predict 清空预测维，避免脏字段外泄
    tt = str(fields.get("target_type") or TargetType.OTHER.value).strip().lower()
    rs = str(fields.get("read_source") or "").strip().lower()
    pc = str(fields.get("predict_channel") or "").strip().lower()
    ta = str(fields.get("time_answer") or "").strip().lower()
    aspect = str(fields.get("predict_aspect") or "").strip().lower()
    is_predict = tt == TargetType.PREDICT.value or (
        tt == TargetType.READ.value and rs == "predict"
    )
    if not is_predict:
        pc, ta, aspect = "", "", ""
        if tt != TargetType.READ.value:
            rs = ""
    else:
        from app.feeding.services.predict_qa import coerce_predict_dims

        pc, ta, aspect, _filled = coerce_predict_dims(pc, ta, aspect or "when")

    return IntentResponse(
        target_type=fields.get("target_type", TargetType.OTHER.value),
        read_source=rs or None,
        predict_channel=pc or None,
        time_answer=ta or None,
        predict_aspect=aspect or None,
        event_name=fields.get("event_name", "") or "",
        event_id=str(fields.get("event_id", "") or ""),
        quantity=fields.get("quantity"),
        event_type=fields.get("event_type"),
        event_unit=fields.get("event_unit"),
        is_new_event=False,
        keywords=fields.get("keywords") or [],
        content=fields.get("content", "") or "",
        events=events,
        remark=fields.get("remark"),
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
    # 查史确认后 speak_history 依赖 history_mode/limit，须写入 pending
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
        remark=fields.get("remark") or "",
        start_time=fields.get("start_time") or fields.get("startTime"),
        end_time=fields.get("end_time") or fields.get("endTime"),
        event_ids=event_ids,
        history_mode=str(fields.get("history_mode") or ""),
        limit=fields.get("limit"),
    )
    return response_from_pending(pending)


def create_predict_confirm_response(
    intent_result: IntentFields,
    *,
    full_events: List[Dict[str, Any]],
    user_input: str,
    device_no: str,
    model_config: Dict[str, Any],
    match_source: str = "",
) -> IntentResponse:
    """
    预测问答软确认：挂 pending，确认后 speak_predict + 飞轮写两维。

    业务说明：
    op 空（非 read），避免确认后续聊被当成查史；预测维塞进 model_config。
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
    mc = dict(model_config or {})
    mc["_type_target"] = TargetType.PREDICT.value
    mc["_type_predict_channel"] = fields.get("predict_channel")
    mc["_type_time_answer"] = fields.get("time_answer")
    mc["_type_predict_aspect"] = fields.get("predict_aspect") or "when"
    if fields.get("keywords"):
        mc["_type_keywords"] = list(fields.get("keywords") or [])
    from app.feeding.services.predict_qa import predict_confirm_sentence

    confirm_message = (
        str(fields.get("confirm_message") or "").strip()
        or predict_confirm_sentence(
            event_name,
            str(fields.get("predict_aspect") or "when"),
            str(fields.get("time_answer") or ""),
        )
    )
    pending = create_leaf_confirm_pending(
        leaf={
            "event_id": event_id or (event_ids[0] if event_ids else ""),
            "event_name": event_name,
            "extra_names": [],
        },
        original_utterance=user_input,
        action="",
        match_source=str(match_source or fields.get("match_source") or ""),
        device_no=device_no,
        model_config=mc,
        events=fields.get("events") or [],
        op="",
        remark=fields.get("remark") or "",
        event_ids=event_ids,
        confirm_message=confirm_message,
    )
    return response_from_pending(pending)


async def try_handle_pending(
    text: str,
    conversation_id: str,
    full_events: List[Dict[str, Any]],
    *,
    on_thinking: Optional[ThinkingCallback] = None,
) -> Tuple[Optional[IntentResponse], bool]:
    """
    处理 pending 续聊。

    Args:
        on_thinking: 流式路径可选；澄清 LLM reasoning 增量回调

    Returns:
        (response, continue_as_new_intent)
        - response 非空：直接返回给客户端
        - continue_as_new_intent=True：清 pending，本句当新意图
    """
    pending = clarification_store.get(conversation_id)
    if not pending:
        return None, False

    result = await resolve_free_text(
        text, pending, full_events=full_events, on_thinking=on_thinking
    )

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
                "event_id": parent_id,
                "event_name": leaf.get("event_name") or "",
                "event_ids": getattr(pending, "event_ids", None) or [parent_id],
                "remark": getattr(pending, "remark", None) or "",
                "events": getattr(pending, "events", None)
                or [
                    {
                        "op": IntentOp.READ.value,
                        "event_id": parent_id,
                        "event_name": leaf.get("event_name") or "",
                        "remark": getattr(pending, "remark", None)
                        or "",
                        "start_time": getattr(pending, "start_time", None),
                        "end_time": getattr(pending, "end_time", None),
                    }
                ],
                "start_time": getattr(pending, "start_time", None),
                "end_time": getattr(pending, "end_time", None),
                "match_source": pending.match_source,
                "match_confidence": 1.0,
            }
            # 查父确认同样回填 mode/limit，避免 daily 回落 point
            hm = str(getattr(pending, "history_mode", None) or "").strip().lower()
            if hm in ("point", "daily"):
                fields["history_mode"] = hm
            if getattr(pending, "limit", None) not in (None, ""):
                fields["limit"] = pending.limit
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
                    op=getattr(pending, "op", None) or "",
                    events=getattr(pending, "events", None) or [],
                    start_time=getattr(pending, "start_time", None),
                    end_time=getattr(pending, "end_time", None),
                    event_ids=getattr(pending, "event_ids", None) or [],
                    history_mode=str(getattr(pending, "history_mode", None) or ""),
                    limit=getattr(pending, "limit", None),
                )
                return response_from_pending(new_pending), False
            return (
                build_intent_response_from_fields(
                    {
                        "target_type": TargetType.CONVERSATION.value,
                        "content": "无法确定具体事件，请重新描述。",
                        "events": [],
                    }
                ),
                False,
            )

        # correct：写原话到正确叶子，且不对旧向量 success++
        # 其余：沿用原飞轮条件
        extra_events = getattr(pending, "events", None) or []
        fields = leaf_intent_result(
            leaf,
            action=pending.action,
            quantity=quantity,
            match_source=pending.match_source,
            match_confidence=1.0,
            original_utterance=pending.original_utterance,
            op=getattr(pending, "op", None) or "",
            events=extra_events or None,
        )
        # 确认后走批量落库或查记录模板
        if extra_events:
            fields["events"] = extra_events
        fields["remark"] = getattr(pending, "remark", None) or ""
        if getattr(pending, "event_ids", None):
            fields["event_ids"] = pending.event_ids
        elif pending_op == IntentOp.READ.value:
            leaf_id = str(leaf.get("event_id") or "")
            fields["event_ids"] = [leaf_id] if leaf_id else []
            fields["target_type"] = TargetType.HISTORY.value
            # 保证 events 含 read
            if not any(
                str(e.get("op") or "") == IntentOp.READ.value
                for e in (fields.get("events") or [])
                if isinstance(e, dict)
            ):
                fields["events"] = [
                    {
                        "op": IntentOp.READ.value,
                        "event_id": leaf_id,
                        "event_name": leaf.get("event_name") or "",
                        "remark": fields.get("remark") or "",
                        "start_time": getattr(pending, "start_time", None),
                        "end_time": getattr(pending, "end_time", None),
                    }
                ]
        if getattr(pending, "start_time", None) is not None:
            fields["start_time"] = pending.start_time
        if getattr(pending, "end_time", None) is not None:
            fields["end_time"] = pending.end_time
        # 查史确认后保留分类 mode/limit，供 speak_history daily 播报
        hm = str(getattr(pending, "history_mode", None) or "").strip().lower()
        if hm in ("point", "daily"):
            fields["history_mode"] = hm
        if getattr(pending, "limit", None) not in (None, ""):
            fields["limit"] = pending.limit
        # TYPE 确认后带回 keywords / 预测维供飞轮写入与播报
        mc = getattr(pending, "model_config", None) or {}
        if isinstance(mc, dict):
            if mc.get("_type_keywords"):
                fields["keywords"] = list(mc.get("_type_keywords") or [])
            if mc.get("_type_target"):
                fields["target_type"] = mc.get("_type_target")
            if mc.get("_type_history_mode") is not None:
                fields["history_mode"] = mc.get("_type_history_mode")
            if mc.get("_type_predict_channel") is not None:
                fields["predict_channel"] = mc.get("_type_predict_channel")
            if mc.get("_type_time_answer") is not None:
                fields["time_answer"] = mc.get("_type_time_answer")
            if mc.get("_type_predict_aspect") is not None:
                fields["predict_aspect"] = mc.get("_type_predict_aspect")
            if mc.get("_type_read_source") is not None:
                fields["read_source"] = mc.get("_type_read_source")
            # EVENT 软候选确认：把选定叶写回 events，并写核词短说法飞轮
            if mc.get("_event_soft_confirm"):
                leaf_id = str(leaf.get("event_id") or "").strip()
                leaf_name = str(leaf.get("event_name") or "").strip()
                fields["event_id"] = leaf_id
                fields["event_name"] = leaf_name
                if leaf_id:
                    fields["event_ids"] = [leaf_id]
                patched_evs: List[Dict[str, Any]] = []
                for e in fields.get("events") or []:
                    if not isinstance(e, dict):
                        continue
                    e2 = dict(e)
                    e2["event_id"] = leaf_id
                    e2["event_name"] = leaf_name
                    patched_evs.append(e2)
                if patched_evs:
                    fields["events"] = patched_evs
                phrase = str(mc.get("_event_soft_phrase") or "").strip()
                if phrase and leaf_id:
                    from app.feeding.services.intent_cache_store import (
                        intent_cache_store,
                    )

                    intent_cache_store.add_event_phrase(
                        phrase,
                        event_id=leaf_id,
                        event_name=leaf_name,
                        kind="leaf",
                    )
                    logger.info(
                        "EVENT 软确认写短说法: phrase=%s event_id=%s",
                        phrase,
                        leaf_id,
                    )
        executed = await _execute_after_confirm(
            fields,
            device_no=pending.device_no,
            user_input=pending.original_utterance,
            full_events=full_events,
        )
        # 确认策略 C 逐段：还有剩余段则继续问下一件
        rest = mc.get("_remaining_events") if isinstance(mc, dict) else None
        if isinstance(rest, list) and rest:
            nxt = rest[0]
            more = rest[1:]
            idx = int(mc.get("_remaining_index") or 2)
            total = int(mc.get("_remaining_total") or (idx + len(more)))
            new_pending = create_leaf_confirm_pending(
                leaf={
                    "event_id": nxt.get("event_id") or "",
                    "event_name": nxt.get("event_name") or "",
                    "extra_names": [],
                },
                original_utterance=pending.original_utterance,
                action=nxt.get("action") or IntentAction.ONE.value,
                quantity=nxt.get("quantity"),
                match_source=pending.match_source,
                matched_vector_id="",
                device_no=pending.device_no,
                model_config={
                    **{k: v for k, v in mc.items() if not str(k).startswith("_")},
                    "_remaining_events": more,
                    "_remaining_index": idx + 1,
                    "_remaining_total": total,
                },
                conversation_id=conversation_id,
                events=[nxt],
                op=str(nxt.get("op") or ""),
                history_mode=str(getattr(pending, "history_mode", None) or ""),
                limit=getattr(pending, "limit", None),
            )
            slot = build_multi_event_confirm_message([nxt]) or nxt.get("event_name")
            new_pending.clarify_message = f"（{idx}/{total}）{slot}？"
            # 附带上一轮回执，便于语音播完再问
            prev = str(executed.get("content") or "").strip()
            resp = response_from_pending(new_pending)
            if prev:
                resp.content = prev
            return resp, False
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
                    "content": "好的，已取消。请重新描述您要记录的事件。",
                    "events": [],
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
    - number 缺量 → 追问毫升
    - 仅显式 need_confirm → leaf_confirm；match_source=llm 不单独强制确认
    - 多段无阻塞 → 直返回（不拼 yes/no）
    - 叶子且无需确认 → 直接返回最终结果（图可能已落库）
    """
    fields = _intent_fields(intent_result)
    from app.feeding.services.intent_events import (
        first_display_event,
        normalize_intent_events,
    )

    fields = normalize_intent_events(fields, full_events)
    # 确认前规则盖时间（与落库前同套），确认话术贴合落库；半命中跳过残缺 clock
    events = [e for e in (fields.get("events") or []) if isinstance(e, dict)]
    if events and (user_input or "").strip():
        new_events, slot_changed = apply_time_slots_to_events(user_input, events)
        if slot_changed:
            fields["events"] = new_events
            events = new_events
            logger.info("确认前规则时间已覆盖: events=%s", len(new_events))

    # number 叶缺量：先追问毫升，不进总确认/落库
    if fields.get("missing_quantity") or any(
        isinstance(e, dict) and e.get("missing_quantity") for e in events
    ):
        name = ""
        for e in events:
            if isinstance(e, dict) and e.get("missing_quantity"):
                name = str(e.get("event_name") or "") or "该事件"
                break
        msg = f"请问「{name}」喝了多少毫升呢？"
        pending = create_leaf_confirm_pending(
            leaf={
                "event_id": events[0].get("event_id") if events else "",
                "event_name": name or (events[0].get("event_name") if events else ""),
                "extra_names": [],
            },
            original_utterance=user_input,
            action=events[0].get("action") if events else IntentAction.ONE.value,
            quantity=None,
            match_source=fields.get("match_source") or MatchSource.NAME.value,
            matched_vector_id=matched_vector_id,
            device_no=device_no,
            model_config=model_config,
            events=events,
            op=str(events[0].get("op") or IntentOp.CREATE.value) if events else "",
            confirm_message=msg,
            history_mode=str(fields.get("history_mode") or ""),
            limit=fields.get("limit"),
        )
        pending.clarify_message = msg
        clarification_store.set(pending)
        return response_from_pending(pending)

    head = first_display_event(fields)
    event_id = str(fields.get("event_id") or head.get("event_id") or "")
    action = str(head.get("action") or IntentAction.ONE.value)
    quantity = fields.get("quantity")
    if quantity is None and head.get("quantity") is not None:
        quantity = head.get("quantity")
    match_source = fields.get("match_source") or MatchSource.LLM.value
    match_confidence = fields.get("match_confidence")

    # 多事件：逐个校验，若含父则整体改消歧（取第一个父）
    if len(events) > 1:
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
                    op=str(ev.get("op") or fields.get("op") or ""),
                    events=events,
                    start_time=fields.get("start_time") or fields.get("startTime"),
                    end_time=fields.get("end_time") or fields.get("endTime"),
                    history_mode=str(fields.get("history_mode") or ""),
                    limit=fields.get("limit"),
                )
                if pending:
                    return response_from_pending(pending)
        # 多事件全是叶子：无阻塞时直执行（图已落库/查史），不再拼 yes/no
        out_fields = {
            **fields,
            "need_confirm": False,
            "confirm_type": None,
            "confirm_message": "",
            "options": [],
            "conversation_id": None,
        }
        return build_intent_response_from_fields(out_fields)

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
            op=str(head.get("op") or ""),
            events=fields.get("events") or [],
            start_time=head.get("start_time")
            or fields.get("start_time")
            or fields.get("startTime"),
            end_time=head.get("end_time")
            or fields.get("end_time")
            or fields.get("endTime"),
            history_mode=str(fields.get("history_mode") or ""),
            limit=fields.get("limit"),
        )
        if pending:
            logger.info(f"匹配结果为父事件，强制消歧: event_id={event_id}")
            return response_from_pending(pending)
        return build_intent_response_from_fields(
            {
                "target_type": TargetType.CONVERSATION.value,
                "content": "该分类下没有可记录的具体事件，请说明具体事项。",
                "match_source": match_source,
                "events": [],
            }
        )

    # 叶子：仅显式 need_confirm（缺量等阻塞）才 pending；llm 命中不再强制确认
    leaf = get_event_by_id(event_id, full_events) or {
        "event_id": event_id,
        "event_name": fields.get("event_name") or head.get("event_name") or "",
    }

    if need_confirm:
        if event_id:
            # 槽位优先子项，便于确认话术反推日段/数量（贴合落库）
            slot_qty = head.get("quantity")
            if slot_qty is None:
                slot_qty = quantity
            # 预测确认后带回通道、问法与 read_source，避免同意后误走查记录
            mc = dict(model_config or {})
            rs_now = str(fields.get("read_source") or "").strip().lower()
            tt_now = str(fields.get("target_type") or "")
            is_pred = tt_now == TargetType.PREDICT.value or (
                tt_now == TargetType.READ.value and rs_now == "predict"
            )
            if fields.get("keywords") or is_pred:
                if fields.get("keywords"):
                    mc["_type_keywords"] = list(fields.get("keywords") or [])
                mc["_type_target"] = fields.get("target_type")
                mc["_type_history_mode"] = fields.get("history_mode")
                mc["_type_read_source"] = fields.get("read_source")
                mc["_type_predict_channel"] = fields.get("predict_channel")
                mc["_type_time_answer"] = fields.get("time_answer")
                mc["_type_predict_aspect"] = fields.get("predict_aspect") or "when"
            pending = create_leaf_confirm_pending(
                leaf=leaf,
                original_utterance=user_input,
                action=action,
                quantity=slot_qty,
                match_source=match_source,
                matched_vector_id=matched_vector_id,
                device_no=device_no,
                model_config=mc,
                events=fields.get("events") or [],
                op=str(head.get("op") or ""),
                remark=fields.get("remark")
                or head.get("remark")
                or "",
                confirm_message=fields.get("confirm_message"),
                start_time=head.get("start_time")
                or fields.get("start_time")
                or fields.get("startTime"),
                end_time=head.get("end_time")
                or fields.get("end_time")
                or fields.get("endTime"),
                history_mode=str(fields.get("history_mode") or ""),
                limit=fields.get("limit"),
            )
            return response_from_pending(pending)

    out_fields = {
        **fields,
        "need_confirm": False,
        "confirm_type": None,
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
    """确认通过后执行 batch、查记录模板或预测播报。"""
    from app.feeding.graphs.nodes.execute_history_crud import execute_history_crud
    from app.feeding.graphs.nodes.speak_history import speak_history
    from app.feeding.graphs.nodes.speak_predict import speak_predict
    from app.feeding.services.history_crud import infer_route_kind
    from app.feeding.services.op_cue_store import op_cue_store
    from app.feeding.services.predict_cue_store import predict_cue_store
    from app.feeding.services.read_source_cue_store import read_source_cue_store
    from app.shared.constants import IntentOp, normalize_target_rail

    # 确认后拆写 OP / R·source / predict 各层（整段）
    doc = (user_input or "").strip()
    tt = normalize_target_rail(str(fields.get("target_type") or ""))
    if doc and tt:
        op_cue_store.add(doc, tt)
        rs_w = str(fields.get("read_source") or "").strip().lower()
        if tt == TargetType.READ.value and rs_w in ("record", "predict"):
            read_source_cue_store.add(doc, rs_w)
        pc_w = str(fields.get("predict_channel") or "").strip().lower()
        ta_w = str(fields.get("time_answer") or "").strip().lower()
        asp_w = str(fields.get("predict_aspect") or "").strip().lower()
        from app.feeding.services.predict_qa import coerce_predict_dims

        pc_w, ta_w, asp_w, filled = coerce_predict_dims(pc_w, ta_w, asp_w or "when")
        if (
            (tt == TargetType.READ.value and rs_w == "predict")
            or tt == TargetType.PREDICT.value
        ) and filled:
            predict_cue_store.add(doc, pc_w, ta_w, asp_w)

    state = {
        "intent_result": fields,
        "device_no": device_no,
        "user_input": user_input,
        "event_dictionary_full": full_events,
        "event_dictionary": full_events,
        "need_confirm": False,
    }
    # R·predict 优先于 R·record / CUD
    tt = str(fields.get("target_type") or "").lower()
    rs = str(fields.get("read_source") or "").lower()
    if tt == TargetType.PREDICT.value or (
        tt == TargetType.READ.value and rs == "predict"
    ):
        out = await speak_predict(state)
    else:
        kind = infer_route_kind(fields)
        if (
            kind == IntentOp.READ.value
            or tt == TargetType.HISTORY.value
            or (tt == TargetType.READ.value and rs != "predict")
        ):
            out = await speak_history(state)
        elif kind == "cud" or tt in (
            TargetType.CREATE.value,
            TargetType.UPDATE.value,
            TargetType.DELETE.value,
            TargetType.FEEDING.value,
        ):
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

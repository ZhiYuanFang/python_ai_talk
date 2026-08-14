"""
喂养意图澄清 / 父事件消歧

业务说明：
同一 /intent 输入框 + conversation_id 续聊。命中父事件时进入 pending，
用自由文本分层解析子选项；硬匹配 miss 后 LLM 澄清；离题则清 pending 当新意图。
"""

from __future__ import annotations

import json
import logging
import re
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.feeding.graphs.nodes.prompts.pending_reply_clarification import (
    build_pending_reply_system_prompt,
    build_pending_reply_user_message,
)
from app.feeding.services.event_hierarchy import (
    get_children,
    get_event_by_id,
    is_parent_event,
    _extra_name_list,
)
from app.shared.constants import (
    ConfirmType,
    IntentAction,
    MatchSource,
    ResolveOp,
    ResolveStatus,
    TargetType,
    VALID_RESOLVE_OPS,
)
from app.shared.llm_client import llm_client, llm_model_config_from_mapping
from app.shared.llm_json import loads_llm_json

logger = logging.getLogger(__name__)

# 兼容：历史 import ResolveStatus from clarification
__all__ = [
    "ResolveStatus",
    "ResolveOp",
    "PendingClarification",
    "ResolveResult",
    "clarification_store",
]

REJECT_WORDS = {
    "取消",
    "不是",
    "算了",
    "不要",
    "不用",
    "不用了",
    "错了",
    "不对",
    "没有",
    "否",
    "别",
    "拒绝",
}

YES_WORDS = {
    "是",
    "对",
    "确认",
    "好",
    "好的",
    "嗯",
    "要",
    "行",
    "可以",
    "没错",
    "是的",
    "对的",
    "嗯嗯",
    "ok",
    "OK",
    "yes",
    "Yes",
}

_ORDINAL_MAP = {
    "1": 0,
    "2": 1,
    "3": 2,
    "4": 3,
    "5": 4,
    "6": 5,
    "7": 6,
    "8": 7,
    "9": 8,
    "10": 9,
    "一": 0,
    "二": 1,
    "三": 2,
    "四": 3,
    "五": 4,
    "六": 5,
    "七": 6,
    "八": 7,
    "九": 8,
    "十": 9,
    "壹": 0,
    "贰": 1,
    "叁": 2,
}


@dataclass
class PendingClarification:
    """待澄清会话状态。"""

    kind: str  # ConfirmType：parent_disambiguation | leaf_confirm
    conversation_id: str
    options: List[Dict[str, Any]]
    clarify_message: str
    original_utterance: str
    action: str = IntentAction.ONE.value
    quantity: Optional[int] = None
    match_source: str = MatchSource.LLM.value
    matched_vector_id: str = ""
    parent_id: str = ""
    parent_name: str = ""
    device_no: str = ""
    model_config: Dict[str, Any] = field(default_factory=dict)
    # 多事件确认与查记录备注：确认后整份执行
    events: List[Dict[str, Any]] = field(default_factory=list)
    op: str = ""
    remark_keyword: str = ""
    # 查记录确认后仍要用分类给出的 unix 窗与原始 event_ids（可能是父 id）
    start_time: Any = None
    end_time: Any = None
    event_ids: List[str] = field(default_factory=list)


@dataclass
class ResolveResult:
    status: ResolveStatus
    event: Optional[Dict[str, Any]] = None
    message: str = ""
    options: Optional[List[Dict[str, Any]]] = None
    # LLM/硬匹配解析出的数量；非 None 时覆盖 pending.quantity
    quantity: Optional[int] = None
    # correct 路径：不对旧向量 matched_vector_id 做 success++
    skip_vector_success: bool = False
    # 内部 ResolveOp（confirm|select|…），非 IntentResponse.action
    action: str = ""


_TRAILING_PUNCT_RE = re.compile(r"[。．.!！?？]+$")
_VALID_LLM_ACTIONS = VALID_RESOLVE_OPS


def normalize_reply_text(text: str) -> str:
    """轻量归一化：strip、剥句末标点、英文 casefold。"""
    t = (text or "").strip()
    t = _TRAILING_PUNCT_RE.sub("", t).strip()
    return t.casefold()


class ClarificationStore:
    """进程内 pending 澄清状态（按 conversation_id）。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pending: Dict[str, PendingClarification] = {}

    def set(self, pending: PendingClarification) -> None:
        with self._lock:
            self._pending[pending.conversation_id] = pending

    def get(self, conversation_id: str) -> Optional[PendingClarification]:
        if not conversation_id:
            return None
        with self._lock:
            return self._pending.get(conversation_id)

    def clear(self, conversation_id: str) -> None:
        if not conversation_id:
            return
        with self._lock:
            self._pending.pop(conversation_id, None)


clarification_store = ClarificationStore()


def build_parent_disambiguation_message(
    parent_name: str, children: List[Dict[str, Any]]
) -> str:
    """生成父事件消歧问句。"""
    lines = [
        f"您提到的是「{parent_name}」。请选择具体事件（回复序号或名称）：",
    ]
    for i, child in enumerate(children, start=1):
        name = child.get("event_name") or ""
        lines.append(f"{i}. {name}")
    return "\n".join(lines)


def build_leaf_confirm_message(
    event_name: str, action: str = IntentAction.ONE.value
) -> str:
    """生成叶子事件确认问句（自由文本回应）。单事件用开始/结束/记录。"""
    action_desc = {
        IntentAction.START.value: "开始记录",
        IntentAction.END.value: "结束记录",
        IntentAction.ONE.value: "记录",
    }.get(action, "记录")
    return f"您是要{action_desc}「{event_name}」吗？请回复确认或取消，也可直接说明具体事件。"


def build_delete_confirm_message(event_name: str) -> str:
    """删除确认：点出事件名与删除，不说成查询历史。"""
    name = (event_name or "").strip() or "该记录"
    return f"您是要删除「{name}」的记录吗？请回复确认或取消。"


def _action_verb_for_confirm(action: str) -> str:
    """
    多事件确认用的短动作词。

    业务说明：end→结束，start→开始，其余→记录。必须点出动作，不能只说「记录以下事件」。
    """
    a = (action or "").strip().lower()
    if a == IntentAction.END.value:
        return "结束"
    if a == IntentAction.START.value:
        return "开始"
    return "记录"


def build_multi_event_confirm_message(events: List[Dict[str, Any]]) -> str:
    """
    多事件确认问句：逐项点出动作与字典名。

    例：您是要结束「爬练习」并开始「坐练习」吗？请回复确认或取消。
    禁止「记录以下事件：爬练习、坐练习」。
    """
    parts: List[str] = []
    for ev in events or []:
        if not isinstance(ev, dict):
            continue
        name = str(ev.get("event_name") or "").strip()
        if not name:
            continue
        verb = _action_verb_for_confirm(str(ev.get("action") or ""))
        parts.append(f"{verb}「{name}」")
    if not parts:
        return ""
    if len(parts) == 1:
        body = parts[0]
    elif len(parts) == 2:
        body = f"{parts[0]}并{parts[1]}"
    else:
        body = "、".join(parts[:-1]) + "并" + parts[-1]
    return f"您是要{body}吗？请回复确认或取消。"


def resolve_event_display_name(
    *,
    event_id: str = "",
    event_name: str = "",
    events: Optional[List[Dict[str, Any]]] = None,
    event_ids: Optional[List[Any]] = None,
) -> str:
    """
    解析确认/播报用的字典事件名。

    业务逻辑：
    优先已有名称；空则按 event_id 回查字典；再退到 event_ids[0]。
    禁止把空名说成「该事件」。
    """
    name = (event_name or "").strip()
    if name:
        return name
    eid = str(event_id or "").strip()
    if not eid and event_ids:
        for item in event_ids:
            if item not in (None, ""):
                eid = str(item)
                break
    if eid and events:
        found = get_event_by_id(eid, events)
        if found:
            return str(found.get("event_name") or "").strip()
    return ""


def build_history_confirm_message(
    event_name: str, remark_keyword: str = ""
) -> str:
    """
    生成查记录确认问句，必须点出事件名；有备注专名时一并点出。

    有名称：请确认是否查询「尿尿」的历史？
    有备注：请确认是否查询「营养品」（按备注 AD）的历史？
    无名（无 id 可查时）：不使用「该事件」兜底。
    """
    name = (event_name or "").strip()
    remark = (remark_keyword or "").strip()
    if not name:
        return "请确认是否查询这条历史记录？请回复确认或取消。"
    if remark:
        return (
            f"请确认是否查询「{name}」（按备注 {remark}）的历史？"
            "请回复确认或取消。"
        )
    return f"请确认是否查询「{name}」的历史？请回复确认或取消。"


def build_remark_disambiguation_message(
    keyword: str, leaves: List[Dict[str, Any]]
) -> str:
    """备注反查多命中：请用户选字典叶子。"""
    kw = (keyword or "").strip() or "该专名"
    lines = [
        f"备注「{kw}」出现在多个事件中，请选择（回复序号或名称）：",
    ]
    for i, leaf in enumerate(leaves, start=1):
        name = leaf.get("event_name") or ""
        lines.append(f"{i}. {name}")
    return "\n".join(lines)


def create_parent_disambiguation_pending(
    *,
    parent: Dict[str, Any],
    children: List[Dict[str, Any]],
    original_utterance: str,
    action: str = IntentAction.ONE.value,
    quantity: Optional[int] = None,
    match_source: str = MatchSource.NAME.value,
    matched_vector_id: str = "",
    device_no: str = "",
    model_config: Optional[Dict[str, Any]] = None,
    conversation_id: Optional[str] = None,
    op: str = "",
    remark_keyword: str = "",
    events: Optional[List[Dict[str, Any]]] = None,
    start_time: Any = None,
    end_time: Any = None,
    event_ids: Optional[List[str]] = None,
    clarify_message: Optional[str] = None,
) -> PendingClarification:
    """创建父事件（或备注多命中）消歧 pending。"""
    cid = conversation_id or str(uuid4())
    parent_name = parent.get("event_name") or ""
    options = [
        {
            "event_id": str(c.get("event_id", "")),
            "event_name": c.get("event_name") or "",
            "extra_names": _extra_name_list(c),
        }
        for c in children
    ]
    message = clarify_message or build_parent_disambiguation_message(
        parent_name, children
    )
    pending = PendingClarification(
        kind=ConfirmType.PARENT_DISAMBIGUATION.value,
        conversation_id=cid,
        options=options,
        clarify_message=message,
        original_utterance=original_utterance,
        action=action or IntentAction.ONE.value,
        quantity=quantity,
        match_source=match_source,
        matched_vector_id=matched_vector_id or "",
        parent_id=str(parent.get("event_id", "")),
        parent_name=parent_name,
        device_no=device_no or "",
        model_config=model_config or {},
        events=events or [],
        op=op or "",
        remark_keyword=remark_keyword or "",
        start_time=start_time,
        end_time=end_time,
        event_ids=[str(x) for x in (event_ids or []) if x not in (None, "")],
    )
    clarification_store.set(pending)
    return pending


def create_remark_disambiguation_pending(
    *,
    keyword: str,
    leaves: List[Dict[str, Any]],
    original_utterance: str,
    action: str = IntentAction.ONE.value,
    quantity: Optional[int] = None,
    match_source: str = MatchSource.LLM.value,
    device_no: str = "",
    model_config: Optional[Dict[str, Any]] = None,
    conversation_id: Optional[str] = None,
    events: Optional[List[Dict[str, Any]]] = None,
    op: str = "",
    start_time: Any = None,
    end_time: Any = None,
) -> PendingClarification:
    """
    备注反查命中多个叶子时的消歧。

    复用 parent_disambiguation 续聊解析；选中后带上 remark_keyword。
    """
    kw = (keyword or "").strip()
    return create_parent_disambiguation_pending(
        parent={"event_id": "", "event_name": kw},
        children=leaves,
        original_utterance=original_utterance,
        action=action,
        quantity=quantity,
        match_source=match_source,
        device_no=device_no,
        model_config=model_config,
        conversation_id=conversation_id,
        op=op,
        remark_keyword=kw,
        events=events,
        start_time=start_time,
        end_time=end_time,
        clarify_message=build_remark_disambiguation_message(kw, leaves),
    )

def create_leaf_confirm_pending(
    *,
    leaf: Dict[str, Any],
    original_utterance: str,
    action: str = IntentAction.ONE.value,
    quantity: Optional[int] = None,
    match_source: str = MatchSource.LLM.value,
    matched_vector_id: str = "",
    device_no: str = "",
    model_config: Optional[Dict[str, Any]] = None,
    conversation_id: Optional[str] = None,
    events: Optional[List[Dict[str, Any]]] = None,
    op: str = "",
    remark_keyword: str = "",
    confirm_message: Optional[str] = None,
    start_time: Any = None,
    end_time: Any = None,
    event_ids: Optional[List[str]] = None,
) -> PendingClarification:
    """创建叶子确认 pending（自由文本是/否）。查记录时话术必带事件名。"""
    cid = conversation_id or str(uuid4())
    event_name = leaf.get("event_name") or ""
    options = [
        {
            "event_id": str(leaf.get("event_id", "")),
            "event_name": event_name,
            "extra_names": _extra_name_list(leaf),
        }
    ]
    resolved_op = (op or "").strip().lower()
    # 查记录确认只认 op=read，不因 action=search 把删除说成查询
    if resolved_op == "read":
        message = build_history_confirm_message(
            event_name, remark_keyword=remark_keyword or ""
        )
    elif resolved_op == "delete":
        message = build_delete_confirm_message(event_name)
    else:
        message = confirm_message or build_leaf_confirm_message(event_name, action)
    pending = PendingClarification(
        kind=ConfirmType.LEAF_CONFIRM.value,
        conversation_id=cid,
        options=options,
        clarify_message=message,
        original_utterance=original_utterance,
        action=action or IntentAction.ONE.value,
        quantity=quantity,
        match_source=match_source,
        matched_vector_id=matched_vector_id or "",
        device_no=device_no or "",
        model_config=model_config or {},
        events=events or [],
        op=op or "",
        remark_keyword=remark_keyword or "",
        start_time=start_time,
        end_time=end_time,
        event_ids=[str(x) for x in (event_ids or []) if x not in (None, "")],
    )
    clarification_store.set(pending)
    return pending


def _parse_ordinal(text: str, option_count: int) -> Optional[int]:
    """解析序号，返回 0-based index。"""
    t = text.strip()
    t = re.sub(r"[.、．)）]\s*$", "", t)
    t = re.sub(r"^[第#]", "", t)
    if t in _ORDINAL_MAP:
        idx = _ORDINAL_MAP[t]
        if 0 <= idx < option_count:
            return idx
        return None
    m = re.fullmatch(r"(\d+)", t)
    if m:
        idx = int(m.group(1)) - 1
        if 0 <= idx < option_count:
            return idx
    return None


def _match_options_by_name(
    text: str, options: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """按名称 / extra_names 硬匹配选项（两侧均归一化比较）。"""
    t = normalize_reply_text(text)
    if not t:
        return []
    matches: List[Dict[str, Any]] = []
    for opt in options:
        name = normalize_reply_text(opt.get("event_name") or "")
        if name and name == t:
            matches.append(opt)
            continue
        extras = opt.get("extra_names") or []
        if any(normalize_reply_text(str(x)) == t for x in extras):
            matches.append(opt)
    return matches


def _reject_words_folded() -> set:
    return {w.casefold() for w in REJECT_WORDS}


def _yes_words_folded() -> set:
    return {w.casefold() for w in YES_WORDS}


def try_hard_resolve(text: str, pending: PendingClarification) -> Optional[ResolveResult]:
    """
    硬匹配解析。命中返回 ResolveResult；未命中返回 None（应交 LLM）。
    空输入返回 ASK_AGAIN（不调 LLM）。
    """
    raw = (text or "").strip()
    if not raw:
        return ResolveResult(
            status=ResolveStatus.ASK_AGAIN,
            message=pending.clarify_message,
            options=pending.options,
        )

    t = normalize_reply_text(raw)
    if not t:
        return ResolveResult(
            status=ResolveStatus.ASK_AGAIN,
            message=pending.clarify_message,
            options=pending.options,
        )

    name_matches = _match_options_by_name(t, pending.options)
    if len(name_matches) == 1:
        return ResolveResult(
            status=ResolveStatus.RESOLVED,
            event=name_matches[0],
            action=ResolveOp.SELECT.value,
        )
    if len(name_matches) > 1:
        msg = build_parent_disambiguation_message(
            pending.parent_name or "该分类", name_matches
        )
        return ResolveResult(
            status=ResolveStatus.ASK_AGAIN,
            message=msg,
            options=name_matches,
            action=ResolveOp.ASK_AGAIN.value,
        )

    ordinal = _parse_ordinal(t, len(pending.options))
    if ordinal is not None:
        return ResolveResult(
            status=ResolveStatus.RESOLVED,
            event=pending.options[ordinal],
            action=ResolveOp.SELECT.value,
        )

    if t in _reject_words_folded():
        return ResolveResult(
            status=ResolveStatus.REJECT, action=ResolveOp.REJECT.value
        )

    if pending.kind == ConfirmType.LEAF_CONFIRM.value and t in _yes_words_folded():
        return ResolveResult(
            status=ResolveStatus.RESOLVED,
            event=pending.options[0] if pending.options else None,
            action=ResolveOp.CONFIRM.value,
        )

    return None


def _parse_llm_clarify_json(content: str) -> Optional[Dict[str, Any]]:
    """解析澄清 LLM JSON；失败返回 None。"""
    try:
        data = loads_llm_json(content)
        if not isinstance(data, dict):
            return None
        return data
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def _find_event_in_dictionary(
    *,
    event_id: Any,
    event_name: str,
    events: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """按 id 或精确名称 / extra_names 查找事件。"""
    if event_id is not None and str(event_id) != "":
        found = get_event_by_id(event_id, events)
        if found:
            return found
    name = (event_name or "").strip()
    if not name:
        return None
    name_key = normalize_reply_text(name)
    for event in events:
        if normalize_reply_text(event.get("event_name") or "") == name_key:
            return event
        extras = _extra_name_list(event)
        if any(normalize_reply_text(x) == name_key for x in extras):
            return event
    return None


def _find_option(
    *,
    event_id: Any,
    event_name: str,
    options: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """在 pending.options 中查找。"""
    eid = str(event_id) if event_id is not None and str(event_id) != "" else ""
    if eid:
        for opt in options:
            if str(opt.get("event_id", "")) == eid:
                return opt
    name_key = normalize_reply_text(event_name or "")
    if name_key:
        matches = _match_options_by_name(name_key, options)
        if len(matches) == 1:
            return matches[0]
    return None


def _coerce_quantity(raw: Any) -> Optional[int]:
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _ask_again_result(pending: PendingClarification) -> ResolveResult:
    return ResolveResult(
        status=ResolveStatus.ASK_AGAIN,
        message=pending.clarify_message,
        options=pending.options,
        action=ResolveOp.ASK_AGAIN.value,
    )


def map_llm_clarify_payload(
    data: Dict[str, Any],
    pending: PendingClarification,
    full_events: List[Dict[str, Any]],
) -> ResolveResult:
    """将 LLM JSON 映射为 ResolveResult；非法则 ask_again。"""
    action = str(data.get("action") or "").strip().lower()
    if action not in _VALID_LLM_ACTIONS:
        return _ask_again_result(pending)

    quantity = _coerce_quantity(data.get("quantity"))
    event_id = data.get("event_id")
    event_name = str(data.get("event_name") or "")

    if action == ResolveOp.ASK_AGAIN.value:
        return _ask_again_result(pending)

    if action == ResolveOp.REJECT.value:
        return ResolveResult(
            status=ResolveStatus.REJECT, action=ResolveOp.REJECT.value
        )

    if action == ResolveOp.NEW_INTENT.value:
        return ResolveResult(
            status=ResolveStatus.OFF_TOPIC, action=ResolveOp.NEW_INTENT.value
        )

    if action == ResolveOp.CONFIRM.value:
        if pending.kind != ConfirmType.LEAF_CONFIRM.value or not pending.options:
            return _ask_again_result(pending)
        return ResolveResult(
            status=ResolveStatus.RESOLVED,
            event=pending.options[0],
            quantity=quantity,
            action=ResolveOp.CONFIRM.value,
        )

    if action == ResolveOp.SELECT.value:
        opt = _find_option(
            event_id=event_id, event_name=event_name, options=pending.options
        )
        if not opt:
            return _ask_again_result(pending)
        return ResolveResult(
            status=ResolveStatus.RESOLVED,
            event=opt,
            quantity=quantity,
            action=ResolveOp.SELECT.value,
        )

    if action == ResolveOp.CORRECT.value:
        target = _find_event_in_dictionary(
            event_id=event_id, event_name=event_name, events=full_events
        )
        if not target:
            # options 内兜底
            opt = _find_option(
                event_id=event_id, event_name=event_name, options=pending.options
            )
            if opt:
                target = opt
        if not target:
            return _ask_again_result(pending)
        return ResolveResult(
            status=ResolveStatus.RESOLVED,
            event={
                "event_id": str(target.get("event_id", "")),
                "event_name": target.get("event_name") or "",
                "extra_names": _extra_name_list(target),
            },
            quantity=quantity,
            skip_vector_success=True,
            action=ResolveOp.CORRECT.value,
        )

    return _ask_again_result(pending)


async def llm_resolve_pending_reply(
    text: str,
    pending: PendingClarification,
    *,
    full_events: List[Dict[str, Any]],
) -> ResolveResult:
    """
    调用 LLM 解析 pending 回复。
    超时 / 异常 / 坏 JSON / 缺动作 → ask_again。
    """
    model_cfg = pending.model_config or {}
    try:
        llm_model_config = llm_model_config_from_mapping(model_cfg)
        user_message = build_pending_reply_user_message(
            text,
            kind=pending.kind,
            clarify_message=pending.clarify_message,
            original_utterance=pending.original_utterance,
            pending_action=pending.action,
            pending_quantity=pending.quantity,
            parent_name=pending.parent_name,
            options=pending.options,
        )
        response = await llm_client.invoke(
            messages=[{"role": "user", "content": user_message}],
            model_config=llm_model_config,
            system_prompt=build_pending_reply_system_prompt(),
        )
        data = _parse_llm_clarify_json(response.content)
        if not data:
            logger.warning(
                "澄清 LLM 返回无法解析为 JSON，ask_again: content=%s",
                (response.content or "")[:200],
            )
            return _ask_again_result(pending)
        return map_llm_clarify_payload(data, pending, full_events)
    except Exception as exc:
        logger.error("澄清 LLM 调用失败，ask_again: %s", exc)
        return _ask_again_result(pending)


async def resolve_free_text(
    text: str,
    pending: PendingClarification,
    *,
    full_events: Optional[List[Dict[str, Any]]] = None,
) -> ResolveResult:
    """
    在 pending 选项语境下解析自由文本。

    顺序：归一化硬匹配（子名/序号/拒绝/肯定）→ miss 则 LLM 澄清。
    """
    hard = try_hard_resolve(text, pending)
    if hard is not None:
        return hard
    return await llm_resolve_pending_reply(
        text, pending, full_events=full_events or []
    )


def try_parent_hit_from_event_id(
    event_id: Any,
    full_events: List[Dict[str, Any]],
    *,
    original_utterance: str,
    action: str = IntentAction.ONE.value,
    quantity: Optional[int] = None,
    match_source: str = MatchSource.VECTOR.value,
    matched_vector_id: str = "",
    device_no: str = "",
    model_config: Optional[Dict[str, Any]] = None,
) -> Optional[PendingClarification]:
    """若 event_id 为父事件，创建消歧 pending 并返回；否则 None。"""
    if not is_parent_event(event_id, full_events):
        return None
    parent = get_event_by_id(event_id, full_events)
    if not parent:
        return None
    children = get_children(event_id, full_events)
    if not children:
        return None
    return create_parent_disambiguation_pending(
        parent=parent,
        children=children,
        original_utterance=original_utterance,
        action=action,
        quantity=quantity,
        match_source=match_source,
        matched_vector_id=matched_vector_id,
        device_no=device_no,
        model_config=model_config,
    )


def pending_to_response_fields(pending: PendingClarification) -> Dict[str, Any]:
    """将 pending 转为 IntentResponse 可用字段。"""
    # 查记录确认对外仍是 history；只认 op=read，不因 action=search 误标
    is_read = (pending.op or "").strip().lower() == "read"
    return {
        "target_type": TargetType.HISTORY.value if is_read else TargetType.FEEDING.value,
        # 澄清态由 need_confirm / confirm_type 表达；action 保留喂养 IntentAction
        "action": pending.action or IntentAction.ONE.value,
        "event_name": pending.parent_name or (
            pending.options[0]["event_name"] if pending.options else ""
        ),
        "event_id": "",
        "quantity": pending.quantity,
        "keywords": [],
        "content": pending.clarify_message,
        "events": pending.events or [],
        "op": pending.op or None,
        "remark_keyword": pending.remark_keyword or None,
        "match_confidence": None,
        "match_source": pending.match_source,
        "need_confirm": True,
        "confirm_type": pending.kind,
        "confirm_message": pending.clarify_message,
        "conversation_id": pending.conversation_id,
        "options": [
            {
                "event_id": o.get("event_id", ""),
                "event_name": o.get("event_name", ""),
                "action": pending.action,
                "quantity": pending.quantity,
            }
            for o in pending.options
        ],
    }


def leaf_intent_result(
    leaf: Dict[str, Any],
    *,
    action: str = IntentAction.ONE.value,
    quantity: Optional[int] = None,
    match_source: str = MatchSource.LLM.value,
    match_confidence: float = 1.0,
    original_utterance: str = "",
) -> Dict[str, Any]:
    """构造已落到唯一叶子的 feeding 意图结果。"""
    resolved_action = action or IntentAction.ONE.value
    return {
        "target_type": TargetType.FEEDING.value,
        "action": resolved_action,
        "event_name": leaf.get("event_name") or "",
        "event_id": str(leaf.get("event_id") or ""),
        "quantity": quantity,
        "keywords": [resolved_action, leaf.get("event_name") or ""],
        "content": "",
        "events": [],
        "match_confidence": match_confidence,
        "match_source": match_source,
        "is_new_event": False,
        "need_confirm": False,
        "confirm_type": None,
        "confirm_message": None,
        "options": [],
        "original_utterance": original_utterance,
    }

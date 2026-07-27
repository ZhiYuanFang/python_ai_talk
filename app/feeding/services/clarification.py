"""
喂养意图澄清 / 父事件消歧

业务说明：
同一 /intent 输入框 + conversation_id 续聊。命中父事件时进入 pending，
用自由文本分层解析子选项；答非所问则清 pending 当新意图。
"""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.feeding.services.event_hierarchy import (
    get_children,
    get_event_by_id,
    is_parent_event,
    _extra_name_list,
)

logger = logging.getLogger(__name__)

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


class ResolveStatus(str, Enum):
    RESOLVED = "resolved"
    ASK_AGAIN = "ask_again"
    REJECT = "reject"
    OFF_TOPIC = "off_topic"


@dataclass
class PendingClarification:
    """待澄清会话状态。"""

    kind: str  # parent_disambiguation | leaf_confirm
    conversation_id: str
    options: List[Dict[str, Any]]
    clarify_message: str
    original_utterance: str
    action: str = "one"
    quantity: Optional[int] = None
    match_source: str = "llm"
    matched_vector_id: str = ""
    parent_id: str = ""
    parent_name: str = ""
    device_no: str = ""
    model_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResolveResult:
    status: ResolveStatus
    event: Optional[Dict[str, Any]] = None
    message: str = ""
    options: Optional[List[Dict[str, Any]]] = None


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


def build_leaf_confirm_message(event_name: str, action: str = "one") -> str:
    """生成叶子事件确认问句（自由文本回应）。"""
    action_desc = {
        "start": "开始记录",
        "end": "结束记录",
        "one": "记录",
    }.get(action, "记录")
    return f"您是要{action_desc}「{event_name}」吗？请回复确认或取消，也可直接说明具体事件。"


def create_parent_disambiguation_pending(
    *,
    parent: Dict[str, Any],
    children: List[Dict[str, Any]],
    original_utterance: str,
    action: str = "one",
    quantity: Optional[int] = None,
    match_source: str = "name",
    matched_vector_id: str = "",
    device_no: str = "",
    model_config: Optional[Dict[str, Any]] = None,
    conversation_id: Optional[str] = None,
) -> PendingClarification:
    """创建父事件消歧 pending。"""
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
    message = build_parent_disambiguation_message(parent_name, children)
    pending = PendingClarification(
        kind="parent_disambiguation",
        conversation_id=cid,
        options=options,
        clarify_message=message,
        original_utterance=original_utterance,
        action=action or "one",
        quantity=quantity,
        match_source=match_source,
        matched_vector_id=matched_vector_id or "",
        parent_id=str(parent.get("event_id", "")),
        parent_name=parent_name,
        device_no=device_no or "",
        model_config=model_config or {},
    )
    clarification_store.set(pending)
    return pending


def create_leaf_confirm_pending(
    *,
    leaf: Dict[str, Any],
    original_utterance: str,
    action: str = "one",
    quantity: Optional[int] = None,
    match_source: str = "llm",
    matched_vector_id: str = "",
    device_no: str = "",
    model_config: Optional[Dict[str, Any]] = None,
    conversation_id: Optional[str] = None,
) -> PendingClarification:
    """创建叶子确认 pending（自由文本是/否）。"""
    cid = conversation_id or str(uuid4())
    event_name = leaf.get("event_name") or ""
    options = [
        {
            "event_id": str(leaf.get("event_id", "")),
            "event_name": event_name,
            "extra_names": _extra_name_list(leaf),
        }
    ]
    message = build_leaf_confirm_message(event_name, action)
    pending = PendingClarification(
        kind="leaf_confirm",
        conversation_id=cid,
        options=options,
        clarify_message=message,
        original_utterance=original_utterance,
        action=action or "one",
        quantity=quantity,
        match_source=match_source,
        matched_vector_id=matched_vector_id or "",
        device_no=device_no or "",
        model_config=model_config or {},
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
    """按名称 / extra_names 硬匹配选项。"""
    t = text.strip()
    if not t:
        return []
    matches: List[Dict[str, Any]] = []
    for opt in options:
        name = (opt.get("event_name") or "").strip()
        if name and name == t:
            matches.append(opt)
            continue
        extras = opt.get("extra_names") or []
        if t in extras:
            matches.append(opt)
    return matches


def resolve_free_text(text: str, pending: PendingClarification) -> ResolveResult:
    """
    在 pending 选项语境下解析自由文本。

    顺序：子名/extra_names → 序号 → 拒绝词 → leaf_confirm 肯定词 → 答非所问。
    """
    t = (text or "").strip()
    if not t:
        return ResolveResult(
            status=ResolveStatus.ASK_AGAIN,
            message=pending.clarify_message,
            options=pending.options,
        )

    name_matches = _match_options_by_name(t, pending.options)
    if len(name_matches) == 1:
        return ResolveResult(status=ResolveStatus.RESOLVED, event=name_matches[0])
    if len(name_matches) > 1:
        msg = build_parent_disambiguation_message(
            pending.parent_name or "该分类", name_matches
        )
        return ResolveResult(
            status=ResolveStatus.ASK_AGAIN,
            message=msg,
            options=name_matches,
        )

    ordinal = _parse_ordinal(t, len(pending.options))
    if ordinal is not None:
        return ResolveResult(
            status=ResolveStatus.RESOLVED, event=pending.options[ordinal]
        )

    # 纯拒绝词（短回复）
    if t in REJECT_WORDS or t.lower() in {w.lower() for w in REJECT_WORDS}:
        return ResolveResult(status=ResolveStatus.REJECT)

    if pending.kind == "leaf_confirm":
        if t in YES_WORDS or t.lower() in {w.lower() for w in YES_WORDS}:
            return ResolveResult(
                status=ResolveStatus.RESOLVED, event=pending.options[0]
            )

    # 答非所问：当新意图
    return ResolveResult(status=ResolveStatus.OFF_TOPIC)


def try_parent_hit_from_event_id(
    event_id: Any,
    full_events: List[Dict[str, Any]],
    *,
    original_utterance: str,
    action: str = "one",
    quantity: Optional[int] = None,
    match_source: str = "vector",
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
    return {
        "target_type": "feeding",
        "action": "disambiguate",
        "event_name": pending.parent_name or (
            pending.options[0]["event_name"] if pending.options else ""
        ),
        "event_id": "",
        "quantity": pending.quantity,
        "keywords": [],
        "content": pending.clarify_message,
        "events": [],
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
    action: str = "one",
    quantity: Optional[int] = None,
    match_source: str = "llm",
    match_confidence: float = 1.0,
    original_utterance: str = "",
) -> Dict[str, Any]:
    """构造已落到唯一叶子的 feeding 意图结果。"""
    return {
        "target_type": "feeding",
        "action": action or "one",
        "event_name": leaf.get("event_name") or "",
        "event_id": str(leaf.get("event_id") or ""),
        "quantity": quantity,
        "keywords": [action or "", leaf.get("event_name") or ""],
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

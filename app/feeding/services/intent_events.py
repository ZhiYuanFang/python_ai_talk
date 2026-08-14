"""
意图 events[] 归一与路由辅助

业务说明：
权威 CRUD/读语义在子项 op 上；顶层不再有 op/action。
兼容旧缓存：若仅有顶层字段则投影为 events[0]。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from app.feeding.services.event_hierarchy import get_event_by_id
from app.shared.constants import IntentAction, IntentOp, TargetType

# 子项合法 op
ITEM_OPS: Set[str] = {
    IntentOp.CREATE.value,
    IntentOp.UPDATE.value,
    IntentOp.DELETE.value,
    IntentOp.READ.value,
    "end",
}
CUD_OPS: Set[str] = {
    IntentOp.CREATE.value,
    IntentOp.UPDATE.value,
    IntentOp.DELETE.value,
    "end",
}


def _is_timer_leaf(leaf: Optional[Dict[str, Any]]) -> bool:
    if not leaf:
        return False
    return str(leaf.get("event_type") or "").strip().lower() == "time"


def derive_item_op(
    ev: Dict[str, Any],
    *,
    leaf: Optional[Dict[str, Any]] = None,
    legacy_top_op: str = "",
) -> str:
    """
    推导子项 op。

    优先显式 op；否则用 action + 字典 type；再否则用旧顶层 op（兼容）。
    """
    raw = str(ev.get("op") or "").strip().lower()
    if raw in ITEM_OPS:
        return raw
    action = str(ev.get("action") or "").strip().lower()
    is_timer = _is_timer_leaf(leaf)
    if action == IntentAction.END.value:
        # 无字典时仍按 end；有字典且非计时则降为 create（由 collect 再盖）
        if leaf is None or is_timer:
            return "end"
        return IntentOp.CREATE.value
    if action in (
        IntentAction.START.value,
        IntentAction.ONE.value,
    ):
        return IntentOp.CREATE.value
    if action == IntentAction.SEARCH.value:
        return IntentOp.READ.value
    top = (legacy_top_op or "").strip().lower()
    if top in ITEM_OPS:
        # 旧顶层 update 不得盖住 start/one
        if top == IntentOp.UPDATE.value and action in (
            IntentAction.START.value,
            IntentAction.ONE.value,
        ):
            return IntentOp.CREATE.value
        return top
    return IntentOp.CREATE.value


def project_legacy_top_level_to_events(intent: Dict[str, Any]) -> Dict[str, Any]:
    """
    若 events 空但顶层仍有 event_id/name/op/action，投影为单元素 events。

    业务说明：意图缓存与过渡期 LLM 漏填数组时用；主路径仍应以数组为准。
    """
    out = dict(intent)
    events = list(out.get("events") or [])
    if events:
        return out
    eid = str(out.get("event_id") or "").strip()
    name = str(out.get("event_name") or "").strip()
    ids = [str(x) for x in (out.get("event_ids") or []) if x not in (None, "")]
    top_op = str(out.get("op") or "").strip().lower()
    top_action = str(out.get("action") or "").strip().lower()
    target = str(out.get("target_type") or "").strip().lower()
    if not eid and not name and not ids:
        return out
    if not eid and ids:
        eid = ids[0]
    item_op = top_op
    if not item_op:
        if target == TargetType.HISTORY.value or top_action == IntentAction.SEARCH.value:
            item_op = IntentOp.READ.value
        elif top_action == IntentAction.END.value:
            item_op = "end"
        elif top_action in (
            IntentAction.START.value,
            IntentAction.ONE.value,
            IntentAction.MULTI.value,
            "",
        ):
            item_op = IntentOp.CREATE.value
        else:
            item_op = IntentOp.CREATE.value
    item: Dict[str, Any] = {
        "op": item_op,
        "action": top_action
        if top_action
        in (
            IntentAction.START.value,
            IntentAction.END.value,
            IntentAction.ONE.value,
        )
        else "",
        "event_id": eid,
        "event_name": name,
        "quantity": out.get("quantity"),
    }
    if item_op == IntentOp.READ.value:
        if out.get("start_time") is not None:
            item["start_time"] = out.get("start_time")
        if out.get("end_time") is not None:
            item["end_time"] = out.get("end_time")
        rk = str(out.get("remark_keyword") or "").strip()
        if rk:
            item["remark_keyword"] = rk
        # 多 id 时拆成多项
        if len(ids) > 1:
            events = []
            for i in ids:
                one = dict(item)
                one["event_id"] = i
                events.append(one)
            out["events"] = events
            return out
    out["events"] = [item]
    return out


def normalize_intent_events(
    intent: Dict[str, Any],
    full_events: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    投影旧顶层 + 为每项补全 op；去掉顶层 op/action 权威。

    返回新 dict，不原地依赖调用方是否保留顶层键（会 pop）。
    """
    out = project_legacy_top_level_to_events(intent)
    legacy_top_op = str(out.get("op") or "").strip().lower()
    full = full_events or []
    normalized: List[Dict[str, Any]] = []
    for ev in out.get("events") or []:
        if not isinstance(ev, dict):
            continue
        item = dict(ev)
        eid = str(item.get("event_id") or "").strip()
        leaf = get_event_by_id(eid, full) if eid and full else None
        item["op"] = derive_item_op(item, leaf=leaf, legacy_top_op=legacy_top_op)
        # 子项 action 仅保留喂养形态
        act = str(item.get("action") or "").strip().lower()
        if act not in (
            IntentAction.START.value,
            IntentAction.END.value,
            IntentAction.ONE.value,
            "",
        ):
            item["action"] = ""
        normalized.append(item)
    out["events"] = normalized
    # 顶层不再作为权威；清除以免下游误用
    out.pop("op", None)
    out.pop("action", None)
    # 由子项推断 target_type（若模型漏标）
    ops = event_ops(out)
    target = str(out.get("target_type") or "").strip().lower()
    if not target or target == TargetType.CONVERSATION.value:
        if ops & {IntentOp.READ.value}:
            out["target_type"] = TargetType.HISTORY.value
        elif ops & CUD_OPS:
            out["target_type"] = TargetType.FEEDING.value
    elif target == TargetType.HISTORY.value and not (ops & {IntentOp.READ.value}):
        # history 但子项未标 read：把无 op 的项补成 read
        fixed = []
        for item in out["events"]:
            it = dict(item)
            if it.get("op") not in ITEM_OPS:
                it["op"] = IntentOp.READ.value
            elif it.get("op") in CUD_OPS and IntentOp.READ.value not in ops:
                pass
            fixed.append(it)
        if any(i.get("op") == IntentOp.READ.value for i in fixed):
            out["events"] = fixed
    return out


def event_ops(intent: Dict[str, Any]) -> Set[str]:
    """收集 events 中的 op 集合。"""
    ops: Set[str] = set()
    for ev in intent.get("events") or []:
        if not isinstance(ev, dict):
            continue
        op = str(ev.get("op") or "").strip().lower()
        if op:
            ops.add(op)
    return ops


def has_cud_events(intent: Dict[str, Any]) -> bool:
    return bool(event_ops(intent) & CUD_OPS)


def has_read_events(intent: Dict[str, Any]) -> bool:
    return IntentOp.READ.value in event_ops(intent)


def first_display_event(intent: Dict[str, Any]) -> Dict[str, Any]:
    """取第一项事件，供确认 pending 展示名等。"""
    for ev in intent.get("events") or []:
        if isinstance(ev, dict):
            return ev
    return {}

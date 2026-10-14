"""
预约事件判定（对齐 Go event.is_appointment）

业务说明：
字典每条事件自带 isAppointment（DB is_appointment，默认 0）。
是否走预约约定 API，只看**命中事件自身**该字段；禁止按根/子树聚合误伤同根日常事件。
与 eventType（number|time|one）正交。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def parse_is_appointment_flag(raw: Any) -> bool:
    """
    解析 isAppointment / is_appointment 标志。

    业务逻辑：
    对齐 Go normalizeIsAppointment：仅 1/true/"1"/"true" 等为真；0/缺省/其它为假。
    """
    if raw is True:
        return True
    if raw is False or raw is None:
        return False
    if isinstance(raw, (int, float)):
        return int(raw) == 1
    s = str(raw).strip().lower()
    return s in ("1", "true", "yes", "y", "on")


def event_is_appointment_flag(ev: Dict[str, Any]) -> bool:
    """单条目录项是否标预约。"""
    if not isinstance(ev, dict):
        return False
    if "is_appointment" in ev:
        return parse_is_appointment_flag(ev.get("is_appointment"))
    return parse_is_appointment_flag(ev.get("isAppointment"))


def find_catalog_event(
    event_id: str,
    catalog: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """按 event_id 查目录项。"""
    eid = str(event_id or "").strip()
    if not eid or not catalog:
        return None
    for e in catalog:
        if not isinstance(e, dict):
            continue
        if str(e.get("event_id") or e.get("id") or "").strip() == eid:
            return e
    return None


def catalog_event_is_appointment(
    event_id: str,
    catalog: List[Dict[str, Any]],
) -> bool:
    """
    命中事件是否为预约（仅看该行 isAppointment）。

    对齐 Go entity.Event.IsAppointment；缺项或缺字段视为非预约。
    """
    ev = find_catalog_event(event_id, catalog)
    if not ev:
        return False
    return event_is_appointment_flag(ev)

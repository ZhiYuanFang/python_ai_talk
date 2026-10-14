"""
预约事件判定（对齐 Flutter appointment_event）

业务说明：
目录根或其子树任一节点 is_appointment 为真时，该根按预约处理：
不走间隔算法，只用 appointment/next 约定 nextAt。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.feeding.services.event_hierarchy import get_root_event_id


def parse_is_appointment_flag(raw: Any) -> bool:
    """
    解析 isAppointment / is_appointment 标志。

    业务逻辑：1/true/"1"/"true" 为真；缺省 false。
    """
    if raw is True:
        return True
    if raw is False or raw is None:
        return False
    if isinstance(raw, (int, float)):
        return int(raw) == 1
    s = str(raw).strip().lower()
    return s in ("1", "true", "yes", "y")


def event_is_appointment_flag(ev: Dict[str, Any]) -> bool:
    """单条目录项是否标预约。"""
    if not isinstance(ev, dict):
        return False
    return parse_is_appointment_flag(
        ev.get("is_appointment")
        if "is_appointment" in ev
        else ev.get("isAppointment")
    )


def catalog_root_is_appointment(
    root_event_id: str,
    catalog: List[Dict[str, Any]],
) -> bool:
    """
    某根（或其子树任一节点标了预约）是否按预约事件处理。

    对齐 Flutter catalogRootIsAppointment。
    """
    root = str(root_event_id or "").strip()
    if not root or not catalog:
        return False
    id_to: Dict[str, Dict[str, Any]] = {}
    for e in catalog:
        if not isinstance(e, dict):
            continue
        eid = str(e.get("event_id") or e.get("id") or "").strip()
        if eid:
            id_to[eid] = e
    root_def = id_to.get(root)
    if root_def and event_is_appointment_flag(root_def):
        return True
    for e in catalog:
        if not isinstance(e, dict) or not event_is_appointment_flag(e):
            continue
        eid = str(e.get("event_id") or e.get("id") or "").strip()
        if not eid:
            continue
        r = get_root_event_id(eid, catalog) or eid
        if r == root:
            return True
    return False


def appointment_root_for_event(
    event_id: str,
    catalog: List[Dict[str, Any]],
) -> Optional[str]:
    """
    若事件所属根为预约，返回根 id；否则 None。
    """
    eid = str(event_id or "").strip()
    if not eid:
        return None
    root = get_root_event_id(eid, catalog) or eid
    if catalog_root_is_appointment(root, catalog):
        return root
    return None

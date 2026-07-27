"""
事件字典层级工具

业务说明：
区分全量事件树与叶子视图。父事件 = event_id 出现在任一非空 parent_id 中。
匹配候选与最终落库仅使用叶子；父名检测与消歧依赖全量树。
"""

from typing import Any, Dict, List, Optional, Set


def parent_id_set(events: List[Dict[str, Any]]) -> Set[str]:
    """收集所有非空 parent_id。"""
    ids: Set[str] = set()
    for event in events:
        raw = event.get("parent_id")
        if raw is None or raw == "":
            continue
        ids.add(str(raw))
    return ids


def is_parent_event(event_id: Any, events: List[Dict[str, Any]]) -> bool:
    """event_id 是否为父事件（被其它事件的 parent_id 引用）。"""
    if event_id is None or event_id == "":
        return False
    return str(event_id) in parent_id_set(events)


def get_leaf_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """派生叶子视图：排除有子节点的父事件。"""
    parents = parent_id_set(events)
    leaves: List[Dict[str, Any]] = []
    for event in events:
        eid = event.get("event_id")
        if eid is None or eid == "":
            continue
        if str(eid) in parents:
            continue
        leaves.append(event)
    return leaves


def get_children(
    parent_id: Any, events: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """返回直接子事件列表。"""
    if parent_id is None or parent_id == "":
        return []
    pid = str(parent_id)
    return [
        e
        for e in events
        if e.get("parent_id") is not None
        and e.get("parent_id") != ""
        and str(e.get("parent_id")) == pid
    ]


def get_event_by_id(
    event_id: Any, events: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """按 event_id 查找事件。"""
    if event_id is None or event_id == "":
        return None
    eid = str(event_id)
    for event in events:
        if str(event.get("event_id", "")) == eid:
            return event
    return None


def _extra_name_list(event: Dict[str, Any]) -> List[str]:
    extras = event.get("extra_names") or []
    if isinstance(extras, str):
        return [extras] if extras else []
    if isinstance(extras, list):
        return [str(x) for x in extras if x is not None and str(x) != ""]
    return []


def find_parent_by_exact_name(
    text: str, events: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    用户文本精确匹配父事件名称（或 extra_names）。
    """
    t = (text or "").strip()
    if not t:
        return None
    parents = parent_id_set(events)
    for event in events:
        eid = event.get("event_id")
        if eid is None or eid == "" or str(eid) not in parents:
            continue
        name = event.get("event_name") or ""
        if name == t:
            return event
        if t in _extra_name_list(event):
            return event
    return None

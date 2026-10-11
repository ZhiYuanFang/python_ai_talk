"""
进行中计时 ETA：匹配与播报文案

业务说明：
消费 Go voice internal GET 的 items，按 historyId→leaf→root 对齐 history 行，
拼出与 Flutter formatActiveTimingEtaLabel 一致的「预计约 HH:mm 结束[ · 已超时]」。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.feeding.services.event_hierarchy import get_root_event_id
from app.shared.history_window import shanghai_tz


def _norm_id(value: Any) -> str:
    """trim 后的 id 字符串；空则 \"\"。"""
    if value is None:
        return ""
    return str(value).strip()


def _ids_equal(a: Any, b: Any) -> bool:
    """
    id 相等：两边非空且字符串相等，或均可解析为同一整数。

    业务说明：
    history 行 id 可能是 int，ETA historyId 为 string；leaf/root 同理。
    """
    sa, sb = _norm_id(a), _norm_id(b)
    if not sa or not sb:
        return False
    if sa == sb:
        return True
    try:
        return int(sa) == int(sb)
    except (TypeError, ValueError):
        return False


def _row_history_id(row: Dict[str, Any]) -> str:
    """历史行主键：id / Id。"""
    for key in ("id", "Id", "historyId", "history_id"):
        v = _norm_id(row.get(key))
        if v:
            return v
    return ""


def _row_leaf_event_id(row: Dict[str, Any]) -> str:
    """历史行叶子事件 id。"""
    for key in ("eventId", "event_id"):
        v = _norm_id(row.get(key))
        if v:
            return v
    return ""


def _parse_unix_sec(value: Any) -> Optional[int]:
    """解析 unix 秒；无效或 ≤0 返回 None。"""
    if value in (None, ""):
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    if n <= 0:
        return None
    return n


def match_expect_end_at(
    row: Dict[str, Any],
    eta_items: List[Dict[str, Any]],
    full_events: List[Dict[str, Any]],
) -> Optional[int]:
    """
    按 historyId → leafEventId → rootEventId 匹配 expectEndAt（unix 秒）。

    Args:
        row: 当前播报的 history 行
        eta_items: Go GET 返回的 items
        full_events: 事件目录（归根用）

    Returns:
        命中项的 expectEndAt；无匹配则 None
    """
    if not row or not eta_items:
        return None

    hid = _row_history_id(row)
    if hid:
        for it in eta_items:
            if _ids_equal(hid, it.get("historyId")):
                end = _parse_unix_sec(it.get("expectEndAt"))
                if end is not None:
                    return end

    leaf = _row_leaf_event_id(row)
    if leaf:
        for it in eta_items:
            if _ids_equal(leaf, it.get("leafEventId")):
                end = _parse_unix_sec(it.get("expectEndAt"))
                if end is not None:
                    return end

    root = get_root_event_id(leaf, full_events) if leaf else ""
    if root:
        for it in eta_items:
            if _ids_equal(root, it.get("rootEventId")):
                end = _parse_unix_sec(it.get("expectEndAt"))
                if end is not None:
                    return end
    return None


def format_eta_clause(
    expect_end_at: int,
    *,
    now: Optional[datetime] = None,
) -> str:
    """
    生成「预计约 HH:mm 结束」或带「 · 已超时」的子句（无前导逗号）。

    业务说明：
    墙钟用 shanghai_tz；超时判定 now > expectEndAt（严格晚于，对齐 App isAfter）。
    """
    tz = shanghai_tz()
    end_dt = datetime.fromtimestamp(int(expect_end_at), tz=tz)
    hhmm = end_dt.strftime("%H:%M")
    base = f"预计约 {hhmm} 结束"
    current = now or datetime.now(tz=tz)
    if current.tzinfo is None:
        current = current.replace(tzinfo=tz)
    else:
        current = current.astimezone(tz)
    if current.timestamp() > float(expect_end_at):
        return f"{base} · 已超时"
    return base


def eta_suffix_for_row(
    row: Dict[str, Any],
    eta_items: Optional[List[Dict[str, Any]]],
    full_events: List[Dict[str, Any]],
    *,
    now: Optional[datetime] = None,
) -> str:
    """
    匹配成功则返回「，预计约 …」；否则空串（调用方保持原话术）。
    """
    if not eta_items:
        return ""
    end = match_expect_end_at(row, eta_items, full_events)
    if end is None:
        return ""
    return "，" + format_eta_clause(end, now=now)

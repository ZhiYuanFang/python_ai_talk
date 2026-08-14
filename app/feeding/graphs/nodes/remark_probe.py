"""
分类前探针：仅进行中计时摘要

业务说明：
缓存未命中时拉近窗历史，筛进行中计时注入分类（不含 history_id）。
备注反查已移到分类后（resolve_remark_event），本节点不再做 OOV 备注 filter。
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List

from app.feeding.services.event_hierarchy import get_event_by_id
from app.shared.graphs.state_patch import state_get
from app.shared.history_window import enum_to_unix, shanghai_tz
from app.shared.http_client import http_client

logger = logging.getLogger(__name__)


def _is_open_end(row: Dict[str, Any]) -> bool:
    """结束时间为空或 0 视为进行中。"""
    raw = row.get("endTime")
    if raw is None:
        raw = row.get("end_time")
    if raw in (None, "", 0, "0"):
        return True
    try:
        return int(raw) == 0
    except (TypeError, ValueError):
        return False


def _row_event_id(row: Dict[str, Any]) -> str:
    return str(row.get("eventId") or row.get("event_id") or "").strip()


def _fmt_start(raw: Any) -> str:
    """Unix 秒格式化为上海墙钟，供提示阅读；失败则原样。"""
    try:
        ts = int(raw)
    except (TypeError, ValueError):
        return str(raw or "")
    if ts <= 0:
        return ""
    return datetime.fromtimestamp(ts, tz=shanghai_tz()).strftime("%Y-%m-%d %H:%M")


def summarize_in_progress(
    rows: List[Dict[str, Any]],
    full_events: List[Dict[str, Any]],
) -> str:
    """
    进行中计时压成提示用一行列表。

    只收字典 event_type=time 且未结束的叶子。不含 history id。
    """
    by_eid: Dict[str, Dict[str, Any]] = {}
    for row in rows or []:
        if not _is_open_end(row):
            continue
        eid = _row_event_id(row)
        if not eid:
            continue
        leaf = get_event_by_id(eid, full_events)
        if not leaf:
            continue
        if str(leaf.get("event_type") or "").strip().lower() != "time":
            continue
        prev = by_eid.get(eid)
        start = row.get("startTime") or row.get("start_time") or 0
        if prev is None:
            by_eid[eid] = {"leaf": leaf, "start": start}
            continue
        try:
            if int(start or 0) >= int(prev.get("start") or 0):
                by_eid[eid] = {"leaf": leaf, "start": start}
        except (TypeError, ValueError):
            by_eid[eid] = {"leaf": leaf, "start": start}
    if not by_eid:
        return "当前无进行中计时。"
    lines = ["当前进行中计时："]
    for eid, item in by_eid.items():
        name = item["leaf"].get("event_name") or eid
        when = _fmt_start(item.get("start"))
        extra = f" 开始于 {when}" if when else ""
        lines.append(f"- {name} id={eid}{extra}")
    return "\n".join(lines)


async def _fetch_recent_rows(device_no: str) -> List[Dict[str, Any]]:
    """近窗小页历史，供进行中筛选。"""
    start_time, end_time = enum_to_unix("last_30_days")
    return await http_client.get_filtered_history_events(
        device_no=device_no,
        event_ids=None,
        start_time=start_time,
        end_time=end_time,
        limit=20,
    )


async def in_progress_probe(state: Any) -> Dict[str, Any]:
    """
    分类前进行中探针：只注入计时摘要。

    缓存已命中则跳过。
    """
    if state_get(state, "intent_cache_hit"):
        return {}
    device_no = state_get(state, "device_no") or ""
    full_events = (
        state_get(state, "event_dictionary_full")
        or state_get(state, "event_dictionary")
        or []
    )
    in_progress_hint = "当前无进行中计时。"
    try:
        recent = await _fetch_recent_rows(device_no)
        in_progress_hint = summarize_in_progress(recent or [], full_events)
    except Exception as exc:
        logger.warning(f"进行中探针失败: {exc}")
        in_progress_hint = "当前无进行中计时。"
    logger.info(f"进行中探针: {in_progress_hint[:80]}")
    return {"in_progress_hint": in_progress_hint}


# 兼容旧节点名导入（图已改用 in_progress_probe）
remark_probe = in_progress_probe

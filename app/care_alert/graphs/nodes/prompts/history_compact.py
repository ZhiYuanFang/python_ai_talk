"""
护理留意历史紧凑注入

业务说明：
将今昨喂养史压成短行，并单独给出 eventName=eventId 对照表，
避免 JSON 全量与史行内重复 id，缩短 care_alert 提示词。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.shared.history_prompt_fields import (
    _parse_epoch,
    _shanghai_tz,
    format_history_time,
)


def _event_id(raw: Dict[str, Any]) -> str:
    """取事件 id（多种别名）。"""
    for key in ("eventId", "event_id", "id"):
        v = raw.get(key)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def _event_name(raw: Dict[str, Any]) -> str:
    """取事件中文名。"""
    name = raw.get("eventName") or raw.get("event_name") or ""
    return str(name).strip() or "未知"


def _event_type(raw: Dict[str, Any]) -> str:
    """
    解析事件类型：number|time|one。

    业务逻辑：
    优先 eventType；缺省时：有起止且时长>=1 秒 → time；
    有 eventNumber → number；否则 one。
    """
    t = raw.get("eventType") or raw.get("event_type") or ""
    t = str(t).strip().lower()
    if t in ("number", "time", "one"):
        return t

    start = raw.get("startTime", raw.get("start_time"))
    end = raw.get("endTime", raw.get("end_time"))
    dt_s = _parse_epoch(start)
    dt_e = _parse_epoch(end)
    if dt_s is not None and dt_e is not None:
        secs = int((dt_e - dt_s).total_seconds())
        if secs >= 1:
            return "time"

    num = raw.get("eventNumber", raw.get("event_number"))
    if num is not None and num != "":
        try:
            float(num)
            return "number"
        except (TypeError, ValueError):
            pass
    return "one"


def _duration_seconds(raw: Dict[str, Any]) -> Optional[int]:
    """计时事件：end-start 秒数；无效则 None。"""
    dt_s = _parse_epoch(raw.get("startTime", raw.get("start_time")))
    dt_e = _parse_epoch(raw.get("endTime", raw.get("end_time")))
    if dt_s is None or dt_e is None:
        return None
    secs = int((dt_e - dt_s).total_seconds())
    if secs < 0:
        return None
    return secs


def _is_today_or_yesterday(raw: Dict[str, Any], now: datetime) -> bool:
    """是否落在上海日历的今天或昨天。"""
    dt = _parse_epoch(raw.get("startTime", raw.get("start_time")))
    if dt is None:
        dt = _parse_epoch(raw.get("endTime", raw.get("end_time")))
    if dt is None:
        return False
    d = dt.date()
    today = now.date()
    yesterday = today - timedelta(days=1)
    return d == today or d == yesterday


def _sort_epoch(raw: Dict[str, Any]) -> float:
    """排序键：start 优先，否则 end。"""
    for candidate in (
        raw.get("startTime", raw.get("start_time")),
        raw.get("endTime", raw.get("end_time")),
    ):
        dt = _parse_epoch(candidate)
        if dt is not None:
            return dt.timestamp()
    return 0.0


def format_care_alert_history_line(
    raw: Dict[str, Any],
    *,
    now: Optional[datetime] = None,
) -> str:
    """
    单条紧凑行：{相对start}{eventName}{后缀}，不含 eventId。

    Returns:
        非空行；无法格式化时返回空串
    """
    now = now or datetime.now(tz=_shanghai_tz())
    start_raw = raw.get("startTime", raw.get("start_time"))
    start_text = format_history_time(start_raw, now=now, style="relative")
    # 按上海日历强制今天/昨天文案（相对 24h 窗口外仍显示「昨天」）
    dt = _parse_epoch(start_raw)
    if dt is not None:
        hm = f"{dt.hour:02d}:{dt.minute:02d}"
        if dt.date() == now.date():
            if start_text in ("刚刚",) or "分钟前" in start_text:
                pass
            else:
                start_text = f"今天 {hm}"
        elif dt.date() == now.date() - timedelta(days=1):
            start_text = f"昨天 {hm}"
    if not start_text:
        return ""
    name = _event_name(raw)
    kind = _event_type(raw)
    if kind == "time":
        secs = _duration_seconds(raw)
        if secs is None:
            suffix = "一次"
        else:
            suffix = f"{secs}秒"
    elif kind == "number":
        num = raw.get("eventNumber", raw.get("event_number"))
        suffix = str(num).strip() if num is not None and str(num).strip() != "" else "0"
    else:
        suffix = "一次"
    return f"{start_text}{name}{suffix}"


def build_care_alert_history_prompt_blocks(
    history_events: List[Dict[str, Any]] | None,
    *,
    now: Optional[datetime] = None,
) -> Tuple[str, str]:
    """
    构建今昨紧凑流水与名→id 对照表。

    Returns:
        (history_lines_text, name_id_legend_text)；无数据时分别为「（无）」与空串
    """
    now = now or datetime.now(tz=_shanghai_tz())
    if not history_events:
        return "（无）", ""

    scored: List[Tuple[float, Dict[str, Any]]] = []
    for raw in history_events:
        if not isinstance(raw, dict):
            continue
        if not _is_today_or_yesterday(raw, now):
            continue
        scored.append((_sort_epoch(raw), raw))
    scored.sort(key=lambda x: x[0], reverse=True)

    lines: List[str] = []
    # 名 → id：按时间从新到旧，先出现的保留（最近）
    name_to_id: Dict[str, str] = {}
    for _, raw in scored:
        line = format_care_alert_history_line(raw, now=now)
        if line:
            lines.append(line)
        name = _event_name(raw)
        eid = _event_id(raw)
        if name and eid and name not in name_to_id:
            name_to_id[name] = eid

    history_text = "\n".join(lines) if lines else "（无）"
    if not name_to_id:
        legend = ""
    else:
        # 对照表按名称排序，稳定可读
        legend_lines = [f"{n}={i}" for n, i in sorted(name_to_id.items(), key=lambda x: x[0])]
        legend = "\n".join(legend_lines)
    return history_text, legend

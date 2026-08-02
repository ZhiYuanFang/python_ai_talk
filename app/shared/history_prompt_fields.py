"""
喂养历史注入 prompt：字段裁剪 + 可读时间 + 最新窗口

业务说明：
Go 返回时间戳与冗余字段；注入 LLM 前裁剪、格式化为上海时区中文，
并按时间降序取最新 N 条，避免模型念不懂 Unix、或拿到最旧片段。
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional, Tuple
from zoneinfo import ZoneInfo

# tip 同源：缺 tzdata 时 UTC+8
_SHANGHAI_FALLBACK = timezone(timedelta(hours=8))

_KEEP_KEYS = (
    "eventName",
    "eventNumber",
    "startTime",
    "endTime",
    "remark",
)

_ALIASES = {
    "event_name": "eventName",
    "event_number": "eventNumber",
    "start_time": "startTime",
    "end_time": "endTime",
}

TimeStyle = Literal["relative", "calendar"]

_SUMMARY_RE = re.compile(
    r"总结|变化|趋势|最近\s*\d+\s*天|最近七天|最近7天|这周|这一周|近一周",
    re.IGNORECASE,
)


def _shanghai_tz():
    try:
        return ZoneInfo("Asia/Shanghai")
    except Exception:
        return _SHANGHAI_FALLBACK


def _parse_epoch(value: Any) -> Optional[datetime]:
    """将秒/毫秒时间戳或数字字符串解析为上海时区 datetime。"""
    if value is None or value == "":
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    # > 1e12 视为毫秒
    if n > 1e12:
        n = n / 1000.0
    if n <= 0:
        return None
    try:
        return datetime.fromtimestamp(n, tz=_shanghai_tz())
    except (OSError, OverflowError, ValueError):
        return None


def format_history_time(
    value: Any,
    *,
    now: Optional[datetime] = None,
    style: TimeStyle = "relative",
) -> str:
    """
    时间戳 → 中文可读。

    relative（点查）：
    - <1 分钟：刚刚
    - <1 小时：N分钟前
    - <1 天：今天/昨天 HH:mm
    - 同年：M月D日 HH:mm
    - 跨年：YYYY年M月D日 HH:mm

    calendar（汇总明细）：同年 M月D日 HH:mm；跨年带年。
    """
    dt = _parse_epoch(value)
    if dt is None:
        return ""
    now = now or datetime.now(tz=_shanghai_tz())
    if now.tzinfo is None:
        now = now.replace(tzinfo=_shanghai_tz())

    hm = f"{dt.hour:02d}:{dt.minute:02d}"

    if style == "calendar":
        if dt.year != now.year:
            return f"{dt.year}年{dt.month}月{dt.day}日 {hm}"
        return f"{dt.month}月{dt.day}日 {hm}"

    # relative
    delta = now - dt
    secs = delta.total_seconds()
    if secs < 0:
        # 未来时间：退回日历
        if dt.year != now.year:
            return f"{dt.year}年{dt.month}月{dt.day}日 {hm}"
        return f"{dt.month}月{dt.day}日 {hm}"
    if secs < 60:
        return "刚刚"
    if secs < 3600:
        return f"{int(secs // 60)}分钟前"

    same_day = dt.date() == now.date()
    yesterday = (now.date() - timedelta(days=1)) == dt.date()
    if secs < 86400:
        if same_day:
            return f"今天 {hm}"
        if yesterday:
            return f"昨天 {hm}"
        return f"{dt.month}月{dt.day}日 {hm}"

    if dt.year != now.year:
        return f"{dt.year}年{dt.month}月{dt.day}日 {hm}"
    return f"{dt.month}月{dt.day}日 {hm}"


def looks_like_summary_query(text: str) -> bool:
    """是否像汇总/趋势类查记录（最近N天总结变化等）。"""
    return bool(_SUMMARY_RE.search((text or "").strip()))


def slim_history_events_for_prompt(
    history_events: List[Dict[str, Any]] | None,
    *,
    limit: int = 20,
    time_style: TimeStyle = "relative",
    now: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    裁剪字段、格式化时间、按 startTime 降序取最新 limit 条。

    Args:
        history_events: 原始历史
        limit: 最多保留条数（最新）
        time_style: relative | calendar
        now: 可注入「现在」便于测试
    """
    if not history_events:
        return []
    now = now or datetime.now(tz=_shanghai_tz())

    scored: List[Tuple[float, Dict[str, Any]]] = []
    for raw in history_events:
        if not isinstance(raw, dict):
            continue
        normalized: Dict[str, Any] = {}
        for k, v in raw.items():
            key = _ALIASES.get(str(k), str(k))
            if key not in _KEEP_KEYS or v is None or v == "":
                continue
            if key in ("startTime", "endTime"):
                text = format_history_time(v, now=now, style=time_style)
                if text:
                    normalized[key] = text
            else:
                normalized[key] = v
        if not normalized:
            continue
        # 排序键：原始 start，缺则 end，再缺则 0
        raw_start = raw.get("startTime", raw.get("start_time"))
        raw_end = raw.get("endTime", raw.get("end_time"))
        epoch = 0.0
        for candidate in (raw_start, raw_end):
            dt = _parse_epoch(candidate)
            if dt is not None:
                epoch = dt.timestamp()
                break
        scored.append((epoch, normalized))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[: max(1, limit)]]


def build_daily_history_summary(
    history_events: List[Dict[str, Any]] | None,
    *,
    now: Optional[datetime] = None,
) -> str:
    """
    按日薄聚合（次数 + eventNumber 求和），供汇总题注入。

    Returns:
        多行文本；无数据返回空串
    """
    if not history_events:
        return ""
    now = now or datetime.now(tz=_shanghai_tz())
    # day_key -> eventName -> {count, sum_num}
    buckets: Dict[str, Dict[str, Dict[str, float]]] = {}

    for raw in history_events:
        if not isinstance(raw, dict):
            continue
        name = raw.get("eventName") or raw.get("event_name") or "未知"
        name = str(name)
        dt = _parse_epoch(raw.get("startTime", raw.get("start_time")))
        if dt is None:
            dt = _parse_epoch(raw.get("endTime", raw.get("end_time")))
        if dt is None:
            continue
        day_key = f"{dt.month}月{dt.day}日"
        if dt.year != now.year:
            day_key = f"{dt.year}年{day_key}"
        day = buckets.setdefault(day_key, {})
        cell = day.setdefault(name, {"count": 0.0, "sum": 0.0})
        cell["count"] += 1
        num = raw.get("eventNumber", raw.get("event_number"))
        try:
            if num is not None and num != "":
                cell["sum"] += float(num)
        except (TypeError, ValueError):
            pass

    if not buckets:
        return ""

    # 按日期粗排：用第一次出现顺序不够；按 day 字符串不稳定。改为解析回 sort
    def _day_sort_key(label: str) -> Tuple[int, int, int]:
        m = re.match(r"(?:(\d+)年)?(\d+)月(\d+)日", label)
        if not m:
            return (0, 0, 0)
        y = int(m.group(1) or now.year)
        return (y, int(m.group(2)), int(m.group(3)))

    lines: List[str] = ["按日汇总（次数 / 数量合计，有数才写合计）："]
    for day_label in sorted(buckets.keys(), key=_day_sort_key):
        parts = []
        for ename, cell in buckets[day_label].items():
            c = int(cell["count"])
            s = cell["sum"]
            if s > 0:
                # 去掉无意义小数
                s_txt = str(int(s)) if s == int(s) else str(s)
                parts.append(f"{ename}{c}次共{s_txt}")
            else:
                parts.append(f"{ename}{c}次")
        lines.append(f"- {day_label}：{'；'.join(parts)}")
    return "\n".join(lines)

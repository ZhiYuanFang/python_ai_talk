"""
时间相对配方：校验与物化

业务说明：
TIME 飞轮只存相对配方（纯 A），禁止以绝对 Unix 作主缓存。
命中后按当前 Asia/Shanghai 物化为 start/end Unix 秒。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.shared.history_window import shanghai_tz

KIND_INSTANT = "instant"
KIND_INTERVAL = "interval"
KIND_DURATION_TO_NOW = "duration_to_now"
KIND_OPEN_START = "open_start"

ALLOWED_KINDS = frozenset(
    {
        KIND_INSTANT,
        KIND_INTERVAL,
        KIND_DURATION_TO_NOW,
        KIND_OPEN_START,
    }
)
ALLOWED_DAYS = frozenset({"today", "yesterday", "day_before"})
ALLOWED_PERIODS = frozenset(
    {"morning", "noon", "afternoon", "evening", "night"}
)
# period 未给 hour 时的默认钟点（Shanghai 墙钟）
_PERIOD_DEFAULT_HOUR = {
    "morning": 8,
    "noon": 12,
    "afternoon": 15,
    "evening": 20,
    "night": 22,
}


def _as_int(raw: Any, *, lo: int, hi: int) -> Optional[int]:
    """解析整数并落在闭区间；非法返回 None。"""
    if raw is None or raw == "":
        return None
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return None
    if n < lo or n > hi:
        return None
    return n


def _normalize_point(raw: Any) -> Optional[Dict[str, Any]]:
    """规范化单个时间点；非法返回 None。"""
    if not isinstance(raw, dict):
        return None
    day = str(raw.get("day") or "").strip().lower()
    if day not in ALLOWED_DAYS:
        return None
    period_raw = raw.get("period")
    period: Optional[str]
    if period_raw is None or period_raw == "":
        period = None
    else:
        period = str(period_raw).strip().lower()
        if period not in ALLOWED_PERIODS:
            return None
    hour = _as_int(raw.get("hour"), lo=0, hi=23)
    minute = _as_int(raw.get("minute"), lo=0, hi=59)
    if minute is None:
        minute = 0
    # 须有 hour，或能从 period 默认
    if hour is None and period is None:
        return None
    return {
        "day": day,
        "period": period,
        "hour": hour,
        "minute": minute,
    }


def validate_time_formula(raw: Any) -> Optional[Dict[str, Any]]:
    """
    校验并规范化相对配方。

    合法返回可序列化 dict；非法返回 None。
    不含 start_time/end_time Unix 字段。
    """
    if not isinstance(raw, dict):
        return None
    kind = str(raw.get("kind") or "").strip().lower()
    if kind not in ALLOWED_KINDS:
        return None

    points_in = raw.get("points")
    if points_in is None:
        points_in = []
    if not isinstance(points_in, list):
        return None
    points: List[Dict[str, Any]] = []
    for p in points_in:
        np = _normalize_point(p)
        if np is None:
            return None
        points.append(np)

    duration = raw.get("duration_minutes")
    duration_n: Optional[int] = None
    if duration is not None and duration != "":
        duration_n = _as_int(duration, lo=1, hi=7 * 24 * 60)
        if duration_n is None:
            return None

    if kind == KIND_INSTANT:
        if len(points) != 1:
            return None
    elif kind == KIND_INTERVAL:
        if len(points) != 2:
            return None
    elif kind == KIND_OPEN_START:
        if len(points) != 1:
            return None
    elif kind == KIND_DURATION_TO_NOW:
        if duration_n is None:
            return None
        # points 可空；若有则忽略（以 duration 为准）
        points = []

    out: Dict[str, Any] = {
        "kind": kind,
        "points": points,
        "duration_minutes": duration_n,
    }
    return out


def _day_delta(day: str) -> int:
    """day 枚举 → 相对今天的天数偏移。"""
    return {"today": 0, "yesterday": -1, "day_before": -2}[day]


def _point_to_datetime(point: Dict[str, Any], now: datetime) -> datetime:
    """将相对点物化为 Shanghai 墙钟 datetime。"""
    base = now.replace(hour=0, minute=0, second=0, microsecond=0)
    base = base + timedelta(days=_day_delta(str(point["day"])))
    hour = point.get("hour")
    minute = int(point.get("minute") or 0)
    period = point.get("period")
    if hour is None:
        if period not in _PERIOD_DEFAULT_HOUR:
            raise ValueError("point 缺少 hour/period")
        hour = _PERIOD_DEFAULT_HOUR[period]
    return base.replace(hour=int(hour), minute=minute, second=0, microsecond=0)


def materialize_time_formula(
    formula: Dict[str, Any],
    *,
    now: Optional[datetime] = None,
) -> Optional[Tuple[int, int]]:
    """
    相对配方 → (start_unix, end_unix)。

    open_start 的 end_unix 为 0。失败返回 None。
    """
    clean = validate_time_formula(formula)
    if not clean:
        return None
    ref = now
    if ref is None:
        ref = datetime.now(tz=shanghai_tz())
    elif ref.tzinfo is None:
        ref = ref.replace(tzinfo=shanghai_tz())
    else:
        ref = ref.astimezone(shanghai_tz())

    kind = clean["kind"]
    try:
        if kind == KIND_DURATION_TO_NOW:
            mins = int(clean["duration_minutes"] or 0)
            if mins <= 0:
                return None
            end_dt = ref
            start_dt = ref - timedelta(minutes=mins)
            return int(start_dt.timestamp()), int(end_dt.timestamp())

        points = clean["points"]
        if kind == KIND_INSTANT:
            st_dt = _point_to_datetime(points[0], ref)
            u = int(st_dt.timestamp())
            return u, u
        if kind == KIND_OPEN_START:
            st_dt = _point_to_datetime(points[0], ref)
            return int(st_dt.timestamp()), 0
        if kind == KIND_INTERVAL:
            st_dt = _point_to_datetime(points[0], ref)
            et_dt = _point_to_datetime(points[1], ref)
            st_u = int(st_dt.timestamp())
            et_u = int(et_dt.timestamp())
            if et_u < st_u:
                return None
            return st_u, et_u
    except (TypeError, ValueError, KeyError):
        return None
    return None

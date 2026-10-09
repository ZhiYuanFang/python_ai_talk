"""
历史时间窗：枚举 → Unix 秒（上海时区）

业务说明：
意图分类应直接给 unix；clinic/tip/care-alert 调用拉史前也先算好 unix，
不再把 today/last_7_days 原样传给 filter。
daily 缺窗时可用原文日词 parse_day_word_window 补窗。
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from zoneinfo import ZoneInfo

_SHANGHAI_FALLBACK = timezone(timedelta(hours=8))

# 对比问：勿收成单日「昨天」
_COMPARE_DAY_RE = re.compile(r"和昨天比|比昨天|和今日比|对比")


def shanghai_tz():
    """上海时区，缺 tzdata 时 UTC+8。"""
    try:
        return ZoneInfo("Asia/Shanghai")
    except Exception:
        return _SHANGHAI_FALLBACK


def now_unix() -> int:
    """当前 Unix 秒。"""
    return int(time.time())

# 最近N天
def last_n_days(n: int) -> Tuple[int, int]:
    return now_unix() - n * 86400, now_unix()

def enum_to_unix(time_range: str, *, now: Optional[int] = None) -> Tuple[int, int]:
    """
    将遗留枚举换成 unix 起止。

    仅作调用方迁移辅助；意图主路径不应再依赖枚举。
    """
    now = now if now is not None else now_unix()
    tz = shanghai_tz()
    now_dt = datetime.fromtimestamp(now, tz=tz)
    today_start = now_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    key = (time_range or "").strip()
    if key == "today":
        return int(today_start.timestamp()), now
    if key == "yesterday":
        start = today_start - timedelta(days=1)
        return int(start.timestamp()), int(today_start.timestamp())
    if key == "day_before_yesterday":
        # 前天：日历日前天 0 点～昨天 0 点
        end = today_start - timedelta(days=1)
        start = today_start - timedelta(days=2)
        return int(start.timestamp()), int(end.timestamp())
    if key == "last_2_days":
        start = today_start - timedelta(days=1)
        return int(start.timestamp()), now
    if key == "last_7_days":
        return now - 7 * 86400, now
    if key == "last_30_days":
        return now - 30 * 86400, now
    # 默认最近 7 天
    return now - 7 * 86400, now


def parse_day_word_window(
    text: str, *, now: Optional[int] = None
) -> Optional[Tuple[int, int]]:
    """
    从原文日词解析 daily 补窗（上海日历）。

    业务逻辑：
    - 「和昨天比」等 → last_2_days（昨 0 点～现在），避免单日昨天
    - 本周/这周 → last_7_days
    - 前天 / 昨天 / 今天 → 对应整日（今天为 0 点～现在）
    - 无日词返回 None（由调用方决定是否默认今天）

    Returns:
        (start, end) 或 None
    """
    raw = text or ""
    if not raw.strip():
        return None
    if _COMPARE_DAY_RE.search(raw):
        return enum_to_unix("last_2_days", now=now)
    if re.search(r"本周|这周", raw):
        return enum_to_unix("last_7_days", now=now)
    if "前天" in raw:
        return enum_to_unix("day_before_yesterday", now=now)
    if re.search(r"昨天|昨日", raw):
        return enum_to_unix("yesterday", now=now)
    if re.search(r"今天|今日", raw):
        return enum_to_unix("today", now=now)
    return None


def resolve_window(data_requirement: Dict[str, Any]) -> Tuple[Optional[int], Optional[int]]:
    """
    优先用已算好的 start_time/end_time（或 startTime/endTime）。
    若只有 time_range 枚举则现场换算（兼容未改完的调用方）。
    """
    start = data_requirement.get("start_time")
    if start is None:
        start = data_requirement.get("startTime")
    end = data_requirement.get("end_time")
    if end is None:
        end = data_requirement.get("endTime")
    try:
        start_i = int(start) if start not in (None, "", 0) else None
    except (TypeError, ValueError):
        start_i = None
    try:
        end_i = int(end) if end not in (None, "", 0) else None
    except (TypeError, ValueError):
        end_i = None
    if start_i or end_i:
        return start_i, end_i
    tr = data_requirement.get("time_range")
    if tr:
        return enum_to_unix(str(tr))
    return None, None

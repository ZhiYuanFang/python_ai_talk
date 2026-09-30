"""
钟点槽位抽取工具

业务说明：
从用户原文抽取「今天/昨天 + N点」类钟点，转为 Asia/Shanghai Unix 秒，
供意图缓存命中后的槽位覆盖使用。不调用 LLM。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from app.shared.history_window import shanghai_tz

logger = logging.getLogger(__name__)

# 汉字小时（含十）
_CN_HOUR = {
    "零": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
    "十一": 11,
    "十二": 12,
}

# 今天/昨天/上午等 + 数字或汉字 + 点/时
_CLOCK_RE = re.compile(
    r"(?:(今天|今日|昨天|昨日|前天))?"
    r"(?:(凌晨|早上|早晨|上午|中午|下午|傍晚|晚上|夜里|晚间))?"
    r"(?P<h>\d{1,2}|[零一二两三四五六七八九十]{1,3})"
    r"(?:点|时)"
    r"(?P<m>\d{1,2}|半)?"
)


@dataclass
class ClockHint:
    """抽到的一个钟点（Unix 秒）。"""

    unix: int
    hour: int
    minute: int
    day_offset: int  # 0=今天, -1=昨天, -2=前天
    raw: str


def _cn_to_hour(token: str) -> Optional[int]:
    """汉字小时 → 0..23；无法识别则 None。"""
    t = (token or "").strip()
    if not t:
        return None
    if t.isdigit():
        return int(t)
    if t in _CN_HOUR:
        return _CN_HOUR[t]
    # 十三～二十三简易：十X / 二十 / 二十X
    if t.startswith("二十") and len(t) >= 2:
        rest = t[2:]
        if not rest:
            return 20
        if rest in _CN_HOUR:
            return 20 + _CN_HOUR[rest]
    if t.startswith("十") and len(t) >= 2:
        rest = t[1:]
        if rest in _CN_HOUR:
            return 10 + _CN_HOUR[rest]
    return None


def _parse_minute(token: Optional[str]) -> int:
    if not token:
        return 0
    if token == "半":
        return 30
    if token.isdigit():
        m = int(token)
        return m if 0 <= m < 60 else 0
    return 0


def _apply_period(hour: int, period: str) -> int:
    """根据上午/下午等调整 12 小时口语。"""
    p = (period or "").strip()
    if not p:
        return hour
    if p in ("下午", "傍晚", "晚上", "夜里", "晚间"):
        if 1 <= hour <= 11:
            return hour + 12
        return hour
    if p == "中午":
        if hour == 0:
            return 12
        if 1 <= hour <= 11:
            return 12 if hour == 12 else (hour if hour >= 11 else hour + 12)
        return hour
    if p in ("凌晨",) and hour == 12:
        return 0
    return hour


def extract_clocks_from_text(
    text: str,
    *,
    now: Optional[datetime] = None,
) -> List[ClockHint]:
    """
    从原文抽取钟点列表（按出现顺序）。

    Args:
        text: 用户输入
        now: 可选「现在」，默认上海当前

    Returns:
        ClockHint 列表；无命中则空列表
    """
    raw = text or ""
    if not raw.strip():
        return []
    base = now.astimezone(shanghai_tz()) if now else datetime.now(shanghai_tz())
    hints: List[ClockHint] = []
    for m in _CLOCK_RE.finditer(raw):
        day_word = m.group(1) or ""
        period = m.group(2) or ""
        h_tok = m.group("h") or ""
        min_tok = m.group("m")
        hour = _cn_to_hour(h_tok)
        if hour is None or hour < 0 or hour > 23:
            continue
        hour = _apply_period(hour, period)
        minute = _parse_minute(min_tok)
        day_offset = 0
        if day_word in ("昨天", "昨日"):
            day_offset = -1
        elif day_word == "前天":
            day_offset = -2
        day = (base + timedelta(days=day_offset)).date()
        try:
            dt = datetime(
                day.year, day.month, day.day, hour, minute, 0, tzinfo=shanghai_tz()
            )
        except ValueError:
            continue
        hints.append(
            ClockHint(
                unix=int(dt.timestamp()),
                hour=hour,
                minute=minute,
                day_offset=day_offset,
                raw=m.group(0),
            )
        )
    if hints:
        logger.debug(
            "钟点抽取: text=%s..., n=%s",
            raw[:40],
            len(hints),
        )
    return hints

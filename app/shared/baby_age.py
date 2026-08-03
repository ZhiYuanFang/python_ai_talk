"""
宝宝月龄与月龄带

业务说明：
从 birthday 按 Asia/Shanghai 日历自算整月月龄；供 tip/clinic 共用。
月龄带用于全局 Q&A 捷径匹配：<36 月按月，≥36 月按年。
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

_SHANGHAI_FALLBACK = timezone(timedelta(hours=8))


def shanghai_tz():
    """返回 Asia/Shanghai；缺 tzdata 时回退 UTC+8。"""
    try:
        return ZoneInfo("Asia/Shanghai")
    except Exception:
        return _SHANGHAI_FALLBACK


def shanghai_now() -> datetime:
    """Asia/Shanghai 当前时刻。"""
    return datetime.now(shanghai_tz())


def parse_birthday_to_date(raw: Any) -> Optional[date]:
    """
    将画像 birthday 解析为 date。

    0 / 空 / 无法解析 → None（未知，不得当作 0 个月）。
    """
    if raw is None or raw == "" or raw == 0:
        return None
    if isinstance(raw, (int, float)):
        ts = int(raw)
        if ts <= 0:
            return None
        return datetime.fromtimestamp(ts, tz=shanghai_tz()).date()
    if isinstance(raw, str):
        text = raw.strip()
        if not text or text == "0":
            return None
        if text.isdigit():
            ts = int(text)
            if ts <= 0:
                return None
            return datetime.fromtimestamp(ts, tz=shanghai_tz()).date()
        try:
            if "T" in text or " " in text:
                return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(
                    shanghai_tz()
                ).date()
            return date.fromisoformat(text[:10])
        except ValueError:
            logger.warning("无法解析 birthday 字符串: %r", text)
            return None
    logger.warning("无法解析 birthday 类型: %s", type(raw))
    return None


def calc_age_months(birth: date, today: date) -> int:
    """日历月差；未来生日钳为 0。"""
    months = (today.year - birth.year) * 12 + (today.month - birth.month)
    if today.day < birth.day:
        months -= 1
    return max(0, months)


def age_months_from_profile(baby_profile: Any) -> Optional[int]:
    """从 baby_profile 推导月龄；未知返回 None。"""
    profile = baby_profile if isinstance(baby_profile, dict) else {}
    birth = parse_birthday_to_date(profile.get("birthday"))
    if birth is None:
        return None
    return calc_age_months(birth, shanghai_now().date())


def age_band_from_months(months: Optional[int]) -> Optional[str]:
    """
    月龄 → 月龄带。

    <36 → m{N}；≥36 → y{Y}（Y=floor(months/12)）；未知 → None。
    """
    if months is None:
        return None
    try:
        m = int(months)
    except (TypeError, ValueError):
        return None
    if m < 0:
        return None
    if m < 36:
        return f"m{m}"
    return f"y{m // 12}"


def format_age_months_text(baby_age_months: Optional[int]) -> str:
    """提示词用月龄文案。"""
    if baby_age_months is None:
        return "未知"
    return f"{baby_age_months} 个月"

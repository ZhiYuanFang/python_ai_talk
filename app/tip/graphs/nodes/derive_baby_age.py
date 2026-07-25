"""
小贴士月龄派生节点

业务说明：
在 tip 图拉取宝宝画像之后，根据 birthday 与 Asia/Shanghai 当前日期自算月龄，
写入 TipState.baby_age_months，供提示词与（若有）知识检索使用。
调用方（Go/Flutter）不再传入月龄。

设计思路：
1. 仅 tip 图使用本节点，不污染 clinic 共享的 fetch_baby_profile
2. 有合法 birthday → 日历月差非负整数；未来生日钳为 0
3. 无 birthday / 无法解析 → 不写入 0，保持缺省（None），提示词侧显示「未知」
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

# 初始化日志记录器
logger = logging.getLogger(__name__)

# 写死上海时区；无 tzdata 时回退到固定 UTC+8（上海无夏令时）
_SHANGHAI_FALLBACK = timezone(timedelta(hours=8))


def shanghai_tz():
    """
    返回 Asia/Shanghai 时区对象。

    业务逻辑：
    优先 ZoneInfo("Asia/Shanghai")；Windows 等环境缺 tzdata 时回退 UTC+8。

    Returns:
        tzinfo 实例
    """
    try:
        return ZoneInfo("Asia/Shanghai")
    except Exception:
        # 容器/本机缺 tzdata 时：上海无 DST，固定 +8 等价
        return _SHANGHAI_FALLBACK


def shanghai_now() -> datetime:
    """
    获取 Asia/Shanghai 当前时刻。

    Returns:
        带时区的 datetime
    """
    return datetime.now(shanghai_tz())


def parse_birthday_to_date(raw: Any) -> Optional[date]:
    """
    将画像中的 birthday 解析为 date。

    业务逻辑：
    history birthday API 返回 Unix 秒（int）；亦兼容日期字符串。
    0 / 空 / 无法解析 → None（表示未知，不得当作 0 个月）。

    Args:
        raw: baby_profile 中的 birthday 字段

    Returns:
        生日 date，或 None
    """
    if raw is None or raw == "" or raw == 0:
        return None
    # Unix 秒（Go DeviceHistoryBirthdayGetRes.birthday）
    if isinstance(raw, (int, float)):
        ts = int(raw)
        if ts <= 0:
            return None
        return datetime.fromtimestamp(ts, tz=shanghai_tz()).date()
    if isinstance(raw, str):
        text = raw.strip()
        if not text or text == "0":
            return None
        # 纯数字字符串按 Unix 秒
        if text.isdigit():
            ts = int(text)
            if ts <= 0:
                return None
            return datetime.fromtimestamp(ts, tz=shanghai_tz()).date()
        # YYYY-MM-DD 或含时间的 ISO
        try:
            if "T" in text or " " in text:
                return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(
                    shanghai_tz()
                ).date()
            return date.fromisoformat(text[:10])
        except ValueError:
            logger.warning(f"无法解析 birthday 字符串: {text!r}")
            return None
    logger.warning(f"无法解析 birthday 类型: {type(raw)}")
    return None


def calc_age_months(birth: date, today: date) -> int:
    """
    按日历月差计算月龄。

    业务逻辑（design 决策 1）：
    (now.year - birth.year) * 12 + (now.month - birth.month)，
    若 now.day < birth.day 则减 1；结果 < 0 时钳为 0（未来生日）。

    Args:
        birth: 生日
        today: 当前日期（Asia/Shanghai）

    Returns:
        非负整数月龄
    """
    months = (today.year - birth.year) * 12 + (today.month - birth.month)
    if today.day < birth.day:
        months -= 1
    return max(0, months)


async def derive_baby_age(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    tip 图节点：根据 baby_profile.birthday 自算月龄。

    业务逻辑：
    1. 读取 fetch_baby_profile 写入的 baby_profile
    2. 解析 birthday；成功则写入 baby_age_months
    3. 失败则显式写入 baby_age_months=None（未知），不得用 0 冒充

    Args:
        state: 当前 tip 图状态

    Returns:
        需更新的 State 字段（含 baby_age_months）
    """
    profile = state.get("baby_profile") or {}
    birth = parse_birthday_to_date(profile.get("birthday"))
    if birth is None:
        # 未知：None，禁止填 0
        logger.info("宝宝月龄未知：无有效 birthday")
        return {"baby_age_months": None}

    today = shanghai_now().date()
    age = calc_age_months(birth, today)
    logger.info(f"宝宝月龄自算: birthday={birth}, today={today}, months={age}")
    return {"baby_age_months": age}

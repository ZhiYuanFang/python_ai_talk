"""
月龄派生节点（tip / clinic 共用）
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.shared.baby_age import calc_age_months, parse_birthday_to_date, shanghai_now

logger = logging.getLogger(__name__)


async def derive_baby_age(state: Dict[str, Any]) -> Dict[str, Any]:
    """根据 baby_profile.birthday 自算月龄；未知则为 None。"""
    profile = state.get("baby_profile") or {}
    birth = parse_birthday_to_date(profile.get("birthday"))
    if birth is None:
        logger.info("宝宝月龄未知：无有效 birthday")
        return {"baby_age_months": None}

    today = shanghai_now().date()
    age = calc_age_months(birth, today)
    logger.info("宝宝月龄自算: birthday=%s, today=%s, months=%s", birth, today, age)
    return {"baby_age_months": age}

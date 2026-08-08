"""
护理留意月龄解析节点

业务说明：
优先用画像 birthday 自算；算不出时回退请求透传的 age_months。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.shared.graphs.nodes.derive_baby_age import derive_baby_age

logger = logging.getLogger(__name__)


async def resolve_baby_age(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    解析月龄：画像派生 → 请求透传兜底。

    Args:
        state: 可含 baby_profile、以及路由预置的 baby_age_months

    Returns:
        {"baby_age_months": int|None}
    """
    # 请求侧预置月龄（Go 可能已算好）
    preset: Optional[int] = None
    if "baby_age_months" in state and state.get("baby_age_months") is not None:
        try:
            preset = int(state.get("baby_age_months"))
        except (TypeError, ValueError):
            preset = None

    derived = await derive_baby_age(state)
    months = derived.get("baby_age_months")
    if months is not None:
        return {"baby_age_months": months}

    if preset is not None:
        logger.info("画像无生日，使用请求透传月龄: %s", preset)
        return {"baby_age_months": preset}

    return {"baby_age_months": None}

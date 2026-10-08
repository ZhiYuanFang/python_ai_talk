"""
时长抽取工具

业务说明：
从原文抽取「N分钟 / N分」，转为秒数，供计时闭合补记（推 end_time）。
MUST NOT 当作毫升 quantity；MUST 忽略「5点46分」里挂在钟点后的分。
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# 先抹掉「N点M分 / N点半」，避免把钟点里的分当成时长
_CLOCK_WITH_MIN_RE = re.compile(
    r"(?:\d{1,2}|[零一二两三四五六七八九十]{1,3})\s*(?:点|时)\s*(?:\d{1,2}分|半)"
)
_DURATION_RE = re.compile(r"(?P<n>\d+)\s*(?:分钟|分(?!钟))")


def extract_duration_seconds(text: str) -> Optional[int]:
    """
    抽取第一个独立时长（秒）。

    Args:
        text: 用户原文

    Returns:
        秒数；未命中或非法则 None
    """
    raw = text or ""
    if not raw.strip():
        return None
    masked = _CLOCK_WITH_MIN_RE.sub(" ", raw)
    m = _DURATION_RE.search(masked)
    if not m:
        return None
    try:
        minutes = int(m.group("n"))
    except (TypeError, ValueError):
        return None
    if minutes <= 0 or minutes > 24 * 60:
        return None
    secs = minutes * 60
    logger.debug("时长抽取: text=%s..., seconds=%s", raw[:40], secs)
    return secs

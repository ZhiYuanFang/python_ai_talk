"""
数量提取工具模块

业务说明：
从用户输入抽取数量，供意图缓存槽位覆盖与分类回填。
必须带「吃了/喝了/喂了」或「毫升/ml」等上下文，或「120配方奶」类名邻接；
MUST 屏蔽「5点」「5:46」等钟点片段，避免把小时/分钟误当成数量。
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)

CHINESE_NUMERALS = {
    "一": "1",
    "二": "2",
    "两": "2",
    "三": "3",
    "四": "4",
    "五": "5",
    "六": "6",
    "七": "7",
    "八": "8",
    "九": "9",
    "十": "10",
}

# 吃了/喝了/喂了 + 数字（单位可选）
_QTY_VERB_RE = re.compile(r"(?:吃了|喝了|喂了)\s*(\d+)\s*(?:毫升|ml|ML|ｍｌ)?")
# 数字 + 毫升/ml（无动词也可）
_QTY_UNIT_RE = re.compile(r"(\d+)\s*(?:毫升|ml|ML|ｍｌ)")
# 「120配方奶」类
_QTY_BEFORE_NAME_RE = re.compile(r"(\d+)\s*(?=配方|母乳|奶粉|辅食|水)")

# 钟点整段：点分 / 冒号，供屏蔽
_CLOCK_SPAN_RE = re.compile(
    r"(?:\d{1,2}|[零一二两三四五六七八九十]{1,3})\s*(?:点|时)\s*(?:\d{1,2}|半)?\s*分?"
    r"|"
    r"\d{1,2}\s*[:：]\s*\d{1,2}"
)


def _replace_chinese_numerals(text: str) -> str:
    """汉字数字转阿拉伯；按长度降序替换。"""
    for chinese, arabic in sorted(
        CHINESE_NUMERALS.items(), key=lambda x: len(x[0]), reverse=True
    ):
        text = text.replace(chinese, arabic)
    return text


def _mask_clock_spans(text: str) -> str:
    """抹掉钟点片段，避免小时/分钟进入数量候选。"""
    return _CLOCK_SPAN_RE.sub(" ", text)


def extract_quantities_from_text(text: str) -> List[int]:
    """
    按出现顺序抽取多个有上下文的数量（已排除钟点数字）。

    Returns:
        数量列表；无则空列表
    """
    if not text or not text.strip():
        return []
    normalized = _replace_chinese_numerals(text)
    masked = _mask_clock_spans(normalized)
    found: List[int] = []
    seen_spans: List[tuple[int, int]] = []

    def _add(match: re.Match[str]) -> None:
        try:
            val = int(match.group(1))
        except (TypeError, ValueError, IndexError):
            return
        span = match.span(1)
        for a, b in seen_spans:
            if not (span[1] <= a or span[0] >= b):
                return
        if val <= 0 or val > 100000:
            return
        seen_spans.append(span)
        found.append(val)

    for m in _QTY_VERB_RE.finditer(masked):
        _add(m)
    for m in _QTY_UNIT_RE.finditer(masked):
        _add(m)
    if not found:
        for m in _QTY_BEFORE_NAME_RE.finditer(masked):
            _add(m)
    if found:
        logger.debug("数量抽取(多): text=%s..., qtys=%s", text[:30], found)
    return found


def extract_quantity_from_text(text: str) -> Optional[int]:
    """
    提取第一个有上下文的数量；未命中则 None。

    Args:
        text: 用户原文

    Returns:
        数量整数或 None
    """
    qtys = extract_quantities_from_text(text)
    if qtys:
        logger.debug(
            "数量提取成功: text='%s...', quantity=%s", text[:30], qtys[0]
        )
        return qtys[0]
    logger.debug("数量提取未命中: text='%s...'", (text or "")[:30])
    return None

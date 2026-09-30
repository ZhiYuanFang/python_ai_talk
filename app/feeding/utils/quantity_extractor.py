"""
数量提取工具模块

业务说明：
从用户输入的自然语言文本中提取数量值，支持汉字数字和阿拉伯数字两种格式。
用于意图缓存命中后的槽位覆盖，以及分类后的数量回填。
优先匹配「毫升/ml/吃了」等上下文，避免把「5点」中的小时误当成数量。
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

# 初始化日志记录器
logger = logging.getLogger(__name__)

# 汉字数字到阿拉伯数字的映射表
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

# 带单位 / 「吃了」上下文的数量（优先）
_QTY_CONTEXT_RE = re.compile(
    r"(?:吃了|喝了|喂了)?\s*(\d+)\s*(?:毫升|ml|ML|ｍｌ)?",
)
# 「120配方奶」类：数字紧挨非「点/时」中文
_QTY_BEFORE_NAME_RE = re.compile(r"(\d+)\s*(?=配方|母乳|奶粉|辅食|水)")
# 钟点片段：用于从候选中排除
_CLOCK_NUM_RE = re.compile(
    r"(?:\d{1,2}|[零一二两三四五六七八九十]{1,3})\s*(?:点|时)"
)


def _replace_chinese_numerals(text: str) -> str:
    """
    将文本中的汉字数字替换为阿拉伯数字。

    业务逻辑：
    遍历汉字数字映射表，将文本中出现的汉字数字逐个替换为对应的阿拉伯数字。
    替换顺序按汉字数字长度降序，避免短字符提前替换导致长字符无法匹配。

    Args:
        text: 原始用户输入文本

    Returns:
        替换后的文本
    """
    # 按汉字数字长度降序排序，避免 "十二" 被拆成 "1" + "二"
    for chinese, arabic in sorted(
        CHINESE_NUMERALS.items(), key=lambda x: len(x[0]), reverse=True
    ):
        text = text.replace(chinese, arabic)
    return text


def _mask_clock_spans(text: str) -> str:
    """把「N点/时」替换为空格，避免小时数字进入数量候选。"""
    return _CLOCK_NUM_RE.sub(" ", text)


def extract_quantities_from_text(text: str) -> List[int]:
    """
    按出现顺序抽取多个数量（排除钟点中的数字）。

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
        # 过滤明显像小时且无单位的 0–23 且前后是点——已 mask；再滤过大异常
        if val <= 0 or val > 100000:
            return
        seen_spans.append(span)
        found.append(val)

    for m in _QTY_CONTEXT_RE.finditer(masked):
        # 若匹配体只有数字、无吃了/毫升，且数字很小，可能是噪音——仍保留（120 等）
        _add(m)
    if not found:
        for m in _QTY_BEFORE_NAME_RE.finditer(masked):
            _add(m)
    if found:
        logger.debug("数量抽取(多): text=%s..., qtys=%s", text[:30], found)
    return found


def extract_quantity_from_text(text: str) -> Optional[int]:
    """
    从用户输入文本中提取数量值（取第一个合理数量）。

    业务逻辑：
    1. 先将汉字数字转换为阿拉伯数字
    2. 屏蔽「N点」片段，优先带毫升/吃了上下文的数字
    3. 返回第一个匹配到的数量；未匹配到则 None

    Args:
        text: 原始用户输入文本

    Returns:
        提取到的数量值（整数），未提取到时返回 None
    """
    qtys = extract_quantities_from_text(text)
    if qtys:
        logger.debug(
            "数量提取成功: text='%s...', quantity=%s", text[:30], qtys[0]
        )
        return qtys[0]
    logger.debug("数量提取未命中: text='%s...'", (text or "")[:30])
    return None

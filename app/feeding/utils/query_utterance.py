"""
历史查询句式检测

业务说明：
含事件名的「上次/什么时候」类问句易被向量高置信打成 feeding。
在 match_event_by_vector 前提示：命中则强制降级 LLM 分类。
"""

from __future__ import annotations

import re

# 查询/询问句式（命中任一则不当作直接落库）
_QUERY_PATTERNS = (
    r"什么时候",
    r"啥时候",
    r"何时",
    r"上一次",
    r"上次",
    r"最近一次",
    r"最近一回",
    r"分别",
    r"多少次",
    r"多少毫升",
    r"多少ml",
    r"吃了多少",
    r"喝了多少",
    r"有没有记录",
    r"查一下",
    r"查查",
)

_QUERY_RE = re.compile("|".join(_QUERY_PATTERNS), re.IGNORECASE)


def looks_like_history_query(text: str) -> bool:
    """
    判断文本是否像历史/统计查询，而非直接记录事件。

    Args:
        text: 用户输入

    Returns:
        True 表示应跳过向量直接 feeding，改走 LLM 分类
    """
    t = (text or "").strip()
    if not t:
        return False
    return _QUERY_RE.search(t) is not None

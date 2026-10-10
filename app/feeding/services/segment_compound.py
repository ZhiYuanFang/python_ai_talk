"""
单事件 / 复合句便宜判定

业务说明：
有明显并列或多重谓语时走分句 LLM；否则整句当一段零 LLM。
吃不准时偏保守：当复合。
"""

from __future__ import annotations

import re

# 并列逗号/顿号 + 多个「了」类谓语尾巴
_COMMA_SPLIT = re.compile(r"[，,、；;]")
_LE_TAIL = re.compile(r"了")
_AND = re.compile(r"和|跟|以及|还有|然后|接着")


def looks_like_compound(text: str) -> bool:
    """
    是否像一句多事。

    Returns:
        True → 需要分句 LLM；False → 可当单事件
    """
    t = (text or "").strip()
    if not t:
        return False
    # 「A和B几次」类查史复合
    if _AND.search(t) and ("几次" in t or "多少次" in t or "什么时候" in t):
        return True
    parts = [p for p in _COMMA_SPLIT.split(t) if p.strip()]
    if len(parts) >= 2:
        return True
    # 无逗号但多个「了」且较长
    if len(_LE_TAIL.findall(t)) >= 2 and len(t) >= 10:
        return True
    return False

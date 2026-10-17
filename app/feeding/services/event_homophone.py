"""
事件名同音替换

业务说明：
ASR 常把事件名听成同音字。解析前用正式名和 extra_names 的带调拼音做唯一替换。
对上零个或多个事件词则不改。对外原话不经过这里。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

# 拼音元组 → 唯一应替换成的词；空表示尚未建索引
_unique: Dict[Tuple[str, ...], str] = {}
_fingerprint = ""
_pinyin_ready: bool | None = None


def _syllables(text: str) -> Tuple[str, ...]:
    """带调拼音。缺库时返回空元组。"""
    global _pinyin_ready
    if _pinyin_ready is False:
        return ()
    try:
        from pypinyin import Style, lazy_pinyin
    except ImportError:
        if _pinyin_ready is not False:
            logger.warning("未安装 pypinyin，跳过事件同音替换")
        _pinyin_ready = False
        return ()
    _pinyin_ready = True
    parts = lazy_pinyin((text or "").strip(), style=Style.TONE3, errors="ignore")
    return tuple(p for p in parts if p)


def rebuild_homophone_index(events: List[Dict[str, Any]]) -> None:
    """按当前事件字典重建唯一同音索引。"""
    global _unique, _fingerprint
    forms: List[str] = []
    for event in events or []:
        name = str(event.get("event_name") or "").strip()
        if name:
            forms.append(name)
        extras = event.get("extra_names") or []
        if isinstance(extras, list):
            for alias in extras:
                word = str(alias or "").strip()
                if word:
                    forms.append(word)
    fp = "\n".join(sorted(set(forms)))
    if fp == _fingerprint:
        return
    buckets: Dict[Tuple[str, ...], set[str]] = {}
    for word in forms:
        key = _syllables(word)
        if len(key) < 2:
            continue
        buckets.setdefault(key, set()).add(word)
    _unique = {key: next(iter(words)) for key, words in buckets.items() if len(words) == 1}
    _fingerprint = fp
    logger.info("事件同音索引已重建: forms=%s unique=%s", len(set(forms)), len(_unique))


def apply_event_homophone(text: str, events: List[Dict[str, Any]]) -> str:
    """
    把句中唯一同音片段换成事件词。

    从左到右取最长片段。没有唯一命中时返回原文。
    """
    raw = (text or "").strip()
    if not raw:
        return raw
    rebuild_homophone_index(events)
    if not _unique or _pinyin_ready is False:
        return raw
    chars = list(raw)
    syls = list(_syllables(raw))
    if len(syls) != len(chars):
        # 拼音与字数对不齐时不替换，避免错位
        return raw
    out: List[str] = []
    i = 0
    n = len(chars)
    while i < n:
        replaced = ""
        for j in range(n, i + 1, -1):
            key = tuple(syls[i:j])
            word = _unique.get(key)
            if word and word != "".join(chars[i:j]):
                replaced = word
                i = j
                break
            if word:
                # 已经是正字，不必改写，但占住这段避免被更短片段拆开
                replaced = "".join(chars[i:j])
                i = j
                break
        if replaced:
            out.append(replaced)
            continue
        out.append(chars[i])
        i += 1
    return "".join(out)

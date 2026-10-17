"""
按词表做近音视图

业务说明：
一段原文只切一次按字对齐的拼音。各维用自己的词表缓存，从原文生成视图。
完全同音优先。否则只允许两种差法里的一种：一个音节声母不同，或一个音节声调不同。韵母必须相同，且只命中一个词。
数字、字母、标点是空位，不参与比对，也不让整句放弃转换。
未安装 pypinyin 时视图等于原文。对外复述不经过这里。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

# 一个汉字的声母、韵母、声调、带调拼音
Syllable = Tuple[str, str, str, str]
# 与字对齐；非汉字为空
Aligned = List[Optional[Syllable]]

# 完全同音：带调元组 → 唯一词
ExactMap = Dict[Tuple[str, ...], str]
# 声母桶：字数+韵母+声调 → (声母元组, 词)
# 声调桶：字数+声母+韵母 → (声调元组, 词)
BucketMap = Dict[Tuple[Any, ...], List[Tuple[Tuple[str, ...], str]]]


class LexiconIndex:
    """一份词表的拼音缓存。请求路径只读，不在这里转写。"""

    def __init__(
        self,
        exact: ExactMap,
        initial_buckets: BucketMap,
        tone_buckets: BucketMap | None = None,
    ) -> None:
        self.exact = exact
        self.initial_buckets = initial_buckets
        self.tone_buckets = tone_buckets or {}


_event_index = LexiconIndex({}, {}, {})
_event_fingerprint = ""
_pinyin_ready: bool | None = None


def pinyin_available() -> bool:
    """拼音库是否可用。缺库时只探测一次。"""
    global _pinyin_ready
    if _pinyin_ready is not None:
        return _pinyin_ready
    try:
        import pypinyin  # noqa: F401
    except ImportError:
        logger.warning("未安装 pypinyin，近音视图等于原文")
        _pinyin_ready = False
        return False
    _pinyin_ready = True
    return True


def _syllable_of(char: str) -> Optional[Syllable]:
    """单个汉字的声母、韵母、声调。非汉字或转不出时返回空。"""
    if not pinyin_available():
        return None
    if not char or not ("\u4e00" <= char <= "\u9fff"):
        return None
    from pypinyin import Style, lazy_pinyin

    tone_rows = lazy_pinyin(char, style=Style.TONE3, errors="ignore")
    if not tone_rows or not tone_rows[0] or not tone_rows[0][0].isalpha():
        return None
    tone3 = tone_rows[0]
    initial_rows = lazy_pinyin(char, style=Style.INITIALS, errors="ignore")
    final_rows = lazy_pinyin(char, style=Style.FINALS, errors="ignore")
    initial = initial_rows[0] if initial_rows else ""
    final = final_rows[0] if final_rows else ""
    tone = tone3[-1] if tone3[-1].isdigit() else ""
    return initial, final, tone, tone3


def cut_segment_pinyin(text: str) -> Optional[Aligned]:
    """
    按字切开原文拼音。

    汉字为音节，数字、字母、标点为空位。缺库时返回 None，调用方保持原文。
    """
    raw = text or ""
    if not raw:
        return []
    if not pinyin_available():
        return None
    return [_syllable_of(ch) for ch in raw]


def _analyze_word(word: str) -> Optional[List[Syllable]]:
    """词表词必须每个字都有音节，且至少两个音节。"""
    chars = list(word)
    if len(chars) < 2:
        return None
    syls: List[Syllable] = []
    for ch in chars:
        syl = _syllable_of(ch)
        if syl is None:
            return None
        syls.append(syl)
    return syls


def build_lexicon_index(words: Sequence[str]) -> LexiconIndex:
    """
    把名词建成完全同音索引、声母分桶和声调分桶。

    同一带调拼音对应多个词时不进入完全同音索引。
    """
    exact_groups: Dict[Tuple[str, ...], set[str]] = {}
    initial_buckets: BucketMap = {}
    tone_buckets: BucketMap = {}
    seen: set[str] = set()
    for raw in words or []:
        word = str(raw or "").strip()
        if not word or word in seen:
            continue
        seen.add(word)
        syls = _analyze_word(word)
        if not syls:
            continue
        tone_key = tuple(item[3] for item in syls)
        exact_groups.setdefault(tone_key, set()).add(word)
        # 声母桶：韵母和声调相同，用来比一个声母
        initial_key: Tuple[Any, ...] = (len(syls),) + tuple(
            (item[1], item[2]) for item in syls
        )
        initial_buckets.setdefault(initial_key, []).append(
            (tuple(item[0] for item in syls), word)
        )
        # 声调桶：声母和韵母相同，用来比一个声调
        tone_bucket_key: Tuple[Any, ...] = (len(syls),) + tuple(
            (item[0], item[1]) for item in syls
        )
        tone_buckets.setdefault(tone_bucket_key, []).append(
            (tuple(item[2] for item in syls), word)
        )
    exact = {
        key: next(iter(group))
        for key, group in exact_groups.items()
        if len(group) == 1
    }
    return LexiconIndex(exact, initial_buckets, tone_buckets)


def _lookup(span: List[Syllable], index: LexiconIndex) -> Optional[str]:
    """完全同音优先。否则一个声母或一个声调不同，且全表只有一个词。"""
    tone_key = tuple(item[3] for item in span)
    exact_hit = index.exact.get(tone_key)
    if exact_hit:
        return exact_hit
    found: List[str] = []
    initial_key: Tuple[Any, ...] = (len(span),) + tuple(
        (item[1], item[2]) for item in span
    )
    heard_initials = tuple(item[0] for item in span)
    for initials, word in index.initial_buckets.get(initial_key, []):
        diffs = sum(1 for a, b in zip(initials, heard_initials) if a != b)
        if diffs == 1 and word not in found:
            found.append(word)
    tone_bucket_key: Tuple[Any, ...] = (len(span),) + tuple(
        (item[0], item[1]) for item in span
    )
    heard_tones = tuple(item[2] for item in span)
    for tones, word in index.tone_buckets.get(tone_bucket_key, []):
        diffs = sum(1 for a, b in zip(tones, heard_tones) if a != b)
        if diffs == 1 and word not in found:
            found.append(word)
    if len(found) == 1:
        return found[0]
    return None


def apply_lexicon_view(
    text: str,
    syllables: Optional[Aligned],
    index: LexiconIndex,
    label: str = "",
) -> str:
    """
    用一份词表把原文转成该维视图。

    从左到右取最长片段。没有音节、缺库或对不齐时返回原文。
    不修改传入的原文和音节。label 非空时写一条是否改写的日志。
    """
    raw = text or ""
    if not raw:
        return raw
    reason = ""
    view = raw
    if syllables is None:
        reason = "no_pinyin"
    elif len(syllables) != len(raw):
        reason = "unaligned"
    elif not index.exact and not index.initial_buckets and not index.tone_buckets:
        reason = "empty_lexicon"
    else:
        chars = list(raw)
        out: List[str] = []
        i = 0
        n = len(chars)
        while i < n:
            replaced = ""
            # 至少两个音节，先试更长的片段
            for j in range(n, i + 1, -1):
                span = syllables[i:j]
                if len(span) < 2 or any(item is None for item in span):
                    continue
                word = _lookup([item for item in span if item is not None], index)
                if not word:
                    continue
                replaced = word
                i = j
                break
            if replaced:
                out.append(replaced)
                continue
            out.append(chars[i])
            i += 1
        view = "".join(out)
        reason = "rewritten" if view != raw else "unchanged"
    if label:
        logger.info(
            "近音转换: dim=%s result=%s raw=%s view=%s",
            label,
            reason,
            raw[:40],
            view[:40],
        )
    return view


def rebuild_homophone_index(events: List[Dict[str, Any]]) -> None:
    """字典载入或手动刷新时重建事件名拼音缓存。"""
    global _event_index, _event_fingerprint
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
    fingerprint = "\n".join(sorted(set(forms)))
    if fingerprint == _event_fingerprint:
        return
    _event_index = build_lexicon_index(forms)
    _event_fingerprint = fingerprint
    logger.info(
        "事件近音缓存已重建: forms=%s exact=%s",
        len(set(forms)),
        len(_event_index.exact),
    )


def apply_event_view(text: str, syllables: Optional[Aligned]) -> str:
    """事件维视图。只读事件缓存，不改原文。"""
    return apply_lexicon_view(text, syllables, _event_index, label="事件")

"""
事件名称规则匹配

业务说明：
把用户或分类给出的名称落到事件字典：精确 → 互相包含 → 剥进行态前缀后再包含。
用于分类落 id，以及备注反查前避免「正在爬」误走备注路径。
extra_names 精确命中：类别/实例别名（如辅食←菠菜），命中时 remark=别名。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# 进行态/口语前缀：剥掉后再与表内名做包含匹配（白名单宜短）
_PROGRESS_PREFIX_RE = re.compile(
    r"^(正在|在|开始|继续|还在)+"
)
# 句末语气助词 / 「了」：别名比较前轻归一
_TRAILING_PARTICLE_RE = re.compile(r"[了啦啊呀哦呢吧]$")


def strip_progress_prefix(name: str) -> str:
    """剥常见进行态前缀，供简称匹配。"""
    t = (name or "").strip()
    if not t:
        return ""
    return _PROGRESS_PREFIX_RE.sub("", t).strip() or t


def normalize_alias_token(text: str) -> str:
    """
    别名/实例词轻归一：去空白、句末语气、进行态前缀。

    供 extra_names 精确比较；不做包含模糊，避免误伤。
    """
    t = (text or "").strip()
    if not t:
        return ""
    t = strip_progress_prefix(t)
    # 可连剥多层句末助词（「菠菜了啊」）
    while t and _TRAILING_PARTICLE_RE.search(t):
        t = _TRAILING_PARTICLE_RE.sub("", t).strip()
    return t


def _alias_candidates(segment: str) -> List[str]:
    """从段文本生成待比候选（原文归一 + 剥前缀变体），保序去重。"""
    raw = (segment or "").strip()
    out: List[str] = []
    for piece in (raw, normalize_alias_token(raw)):
        if piece and piece not in out:
            out.append(piece)
    return out


def match_extra_names(
    segment: str, event_dictionary: List[Dict[str, Any]]
) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], str]:
    """
    全表 extra_names 精确命中（类别/实例别名）。

    Returns:
        (唯一命中事件或 None, 全部命中事件列表, 命中的别名词原文)
        多事件命中同一别名时唯一项为 None，列表长度>1，供消歧。
    """
    candidates = _alias_candidates(segment)
    if not candidates:
        return None, [], ""

    # 归一化候选集合，便于 O(1) 判断
    cand_norm = {normalize_alias_token(c) for c in candidates if c}
    cand_norm |= {c for c in candidates if c}

    hits: List[Tuple[Dict[str, Any], str]] = []
    seen_ids: set[str] = set()
    for event in event_dictionary or []:
        extras = event.get("extra_names") or []
        if not isinstance(extras, list):
            continue
        matched_alias = ""
        for alias in extras:
            a = str(alias or "").strip()
            if not a:
                continue
            an = normalize_alias_token(a)
            if a in cand_norm or an in cand_norm:
                matched_alias = a
                break
        if not matched_alias:
            continue
        eid = str(event.get("event_id") or "")
        if eid and eid in seen_ids:
            continue
        if eid:
            seen_ids.add(eid)
        hits.append((event, matched_alias))

    if not hits:
        return None, [], ""
    if len(hits) == 1:
        ev, alias = hits[0]
        return ev, [ev], alias
    # 多事件：别名取首个命中词（通常相同）
    alias = hits[0][1]
    return None, [h[0] for h in hits], alias


def match_feeding_event(
    event_name: str, event_dictionary: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    在事件字典（全量树，含父）中匹配事件。

    业务逻辑：
    1. 精确匹配名称（父名优先于后续模糊）
    2. 互相包含匹配
    3. 剥「正在/在/开始」等前缀后再包含（「正在爬」→「爬练习」）

    Args:
        event_name: 用户或 LLM 给出的事件名称
        event_dictionary: 全量事件字典列表

    Returns:
        匹配到的事件字典，未匹配到时返回 None
    """
    name = (event_name or "").strip()
    if not name:
        return None

    # 精确匹配
    for event in event_dictionary:
        if (event.get("event_name") or "") == name:
            return event

    # 互相包含
    for event in event_dictionary:
        en = event.get("event_name") or ""
        if en and (name in en or en in name):
            return event

    # 剥进行态前缀后再包含（避免「正在爬」进备注反查）
    stripped = strip_progress_prefix(name)
    if stripped and stripped != name:
        for event in event_dictionary:
            en = event.get("event_name") or ""
            if en and (stripped in en or en in stripped):
                return event

    return None

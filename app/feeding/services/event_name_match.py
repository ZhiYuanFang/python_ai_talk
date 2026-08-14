"""
事件名称规则匹配

业务说明：
把用户或分类给出的名称落到事件字典：精确 → 互相包含 → 剥进行态前缀后再包含。
用于分类落 id，以及备注反查前避免「正在爬」误走备注路径。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# 进行态/口语前缀：剥掉后再与表内名做包含匹配（白名单宜短）
_PROGRESS_PREFIX_RE = re.compile(
    r"^(正在|在|开始|继续|还在)+"
)


def strip_progress_prefix(name: str) -> str:
    """剥常见进行态前缀，供简称匹配。"""
    t = (name or "").strip()
    if not t:
        return ""
    return _PROGRESS_PREFIX_RE.sub("", t).strip() or t


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

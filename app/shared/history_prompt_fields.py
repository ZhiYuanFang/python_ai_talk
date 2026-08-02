"""
喂养历史注入 prompt 前的字段裁剪

业务说明：
Go 返回的历史记录字段很多，进 LLM 只保留答题所需字段，省 token、降噪。
"""

from __future__ import annotations

from typing import Any, Dict, List

# 约定保留字段（camelCase，与 Go 侧常见命名对齐）
_KEEP_KEYS = (
    "eventName",
    "eventNumber",
    "startTime",
    "endTime",
    "remark",
)

# 若上游偶发 snake_case，映射到上述权威名
_ALIASES = {
    "event_name": "eventName",
    "event_number": "eventNumber",
    "start_time": "startTime",
    "end_time": "endTime",
}


def slim_history_events_for_prompt(
    history_events: List[Dict[str, Any]] | None,
) -> List[Dict[str, Any]]:
    """
    将历史记录裁成 prompt 用精简列表；缺字段则省略该 key。

    Args:
        history_events: 原始历史列表

    Returns:
        仅含约定字段的新列表（不修改入参）
    """
    if not history_events:
        return []
    slimmed: List[Dict[str, Any]] = []
    for raw in history_events:
        if not isinstance(raw, dict):
            continue
        # 先按别名归一
        normalized: Dict[str, Any] = {}
        for k, v in raw.items():
            key = _ALIASES.get(str(k), str(k))
            if key in _KEEP_KEYS and v is not None and v != "":
                normalized[key] = v
        if normalized:
            slimmed.append(normalized)
    return slimmed

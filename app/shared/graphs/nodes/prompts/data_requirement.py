"""
数据需求判断提示词构建模块

业务说明：
构建数据需求判断节点使用的系统提示词，引导 LLM 根据用户问题判断需要查询哪些事件类型的历史记录以及时间范围。
输出使用 event_ids（事件ID）而非事件名称，因为事件ID是稳定标识，名称可能变化。

设计思路：
1. 输入事件字典（id + name），输出 event_ids
2. 定义 time_range 可选值（today, yesterday, last_7_days, last_30_days, custom）
3. 提供 limit 字段用于限制返回数量
4. 要求严格 JSON 格式返回
"""

import json
from typing import Any, Dict, List

from app.shared.graphs.nodes.prompts.system import DATA_REQUIREMENT_SYSTEM_PROMPT


def build_data_requirement_system_prompt() -> str:
    """
    构建数据需求判断的系统提示词

    业务逻辑：
    引导 LLM 根据用户问题分析需要查询哪些类型的历史记录以及时间范围。
    输出 event_ids（事件ID列表），因为事件ID是稳定标识，名称可能变化。

    Returns:
        系统提示词字符串
    """
    return DATA_REQUIREMENT_SYSTEM_PROMPT


def build_data_requirement_user_message(user_text: str, event_dictionary: List[Dict[str, Any]]) -> str:
    """
    构建数据需求判断的用户消息

    业务逻辑：
    将用户问题和可用事件列表组合成用户消息。
    可用事件展示 id + name，方便 LLM 理解和选择。

    Args:
        user_text: 用户的问题文本
        event_dictionary: 事件字典列表，每个元素包含 event_id, event_name 等字段

    Returns:
        用户消息字符串
    """
    # 将事件字典格式化为 id + name 的简化列表（id 以字符串展示）
    events_simple = []
    for e in event_dictionary:
        raw_id = e.get("event_id", e.get("id", ""))
        eid = "" if raw_id is None else str(raw_id)
        events_simple.append({"id": eid, "name": e.get("event_name", "")})
    events_str = json.dumps(events_simple, ensure_ascii=False, indent=2)

    return f"""
用户问题："{user_text}"

可用事件：
{events_str}

请分析用户问题，判断需要查询哪些类型的历史记录以及时间范围。
只输出 JSON 格式的结果。
"""

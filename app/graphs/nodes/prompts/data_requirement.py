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


def build_data_requirement_system_prompt() -> str:
    """
    构建数据需求判断的系统提示词

    业务逻辑：
    引导 LLM 根据用户问题分析需要查询哪些事件类型的历史记录以及时间范围。
    输出 event_ids（事件ID列表），因为事件ID是稳定标识，名称可能变化。

    Returns:
        系统提示词字符串
    """
    return f"""
你是一个专业的数据分析助手。
请分析用户的问题，判断需要查询哪些类型的历史记录以及时间范围。

输出格式：
{{
    "event_ids": [1, 2],
    "time_range": "today",
    "limit": 20
}}

time_range 可选值：
- "today": 今天（00:00 ~ 现在）
- "yesterday": 昨天
- "last_7_days": 最近7天
- "last_30_days": 最近30天
- "custom": 自定义时间范围（需同时提供 start_time 和 end_time）

注意事项：
1. event_ids 使用事件的数字ID，从可用事件中选择
2. 如果用户问题涉及所有喂养事件，返回所有相关事件的ID
3. 如果无法确定具体事件，返回空列表（表示拉取所有类型）
4. limit 字段表示需要返回的记录数量上限，默认20条
5. 返回结果必须是合法的 JSON 格式
6. 只返回 JSON，不要有任何额外的解释文字
"""


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
    # 将事件字典格式化为 id + name 的简化列表
    events_simple = [
        {"id": e.get("event_id", e.get("id", "")), "name": e.get("event_name", "")}
        for e in event_dictionary
    ]
    events_str = json.dumps(events_simple, ensure_ascii=False, indent=2)

    return f"""
用户问题："{user_text}"

可用事件：
{events_str}

请分析用户问题，判断需要查询哪些类型的历史记录以及时间范围。
只输出 JSON 格式的结果。
"""

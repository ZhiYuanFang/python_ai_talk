"""
history 意图回答生成提示词构建模块

业务说明：
构建 history 意图（历史查询）回答生成节点使用的系统提示词。
引导 LLM 根据历史记录生成自然语言的历史查询回答。

设计思路：
1. 将历史记录格式化为上下文注入提示词
2. 要求 LLM 用自然语言总结历史数据
3. 回答风格要友好、清晰、易懂
"""

import json
from typing import Any, Dict, List


def build_history_answer_system_prompt() -> str:
    """
    构建 history 意图回答生成的系统提示词

    业务逻辑：
    引导 LLM 根据历史记录生成自然语言回答。
    回答要清晰、有条理，用用户容易理解的方式呈现数据。

    Returns:
        系统提示词字符串
    """
    return """
你是一个专业的母婴喂养助手。
请根据提供的历史记录，用自然语言回答用户的问题。

回答要求：
1. 回答要清晰、准确，基于历史记录数据
2. 用友好的语气，适合与家长交流
3. 如果历史记录为空，要如实告知用户
4. 回答中可以包含关键数据（如总量、次数、平均值等）
5. 不要编造记录中没有的数据
6. 回答要简洁，不要过于冗长
"""


def build_history_answer_user_message(user_text: str, history_events: List[Dict[str, Any]]) -> str:
    """
    构建 history 意图回答生成的用户消息

    业务逻辑：
    将用户问题和历史记录组合成用户消息。

    Args:
        user_text: 用户的问题文本
        history_events: 历史记录列表

    Returns:
        用户消息字符串
    """
    history_str = json.dumps(history_events, ensure_ascii=False, indent=2)

    return f"""
用户问题："{user_text}"

历史记录：
{history_str}

请根据以上历史记录，用自然语言回答用户的问题。
"""

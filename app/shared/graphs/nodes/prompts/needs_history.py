"""
是否需要喂养历史：门禁提示词

业务说明：
在 judge_data_requirement（范围）之前，先判断回答是否需要参考喂养历史记录。
宽松策略：可能有用就 true；仅纯闲聊/与宝宝近期记录无关的通用知识才 false。

设计思路：
1. 只输出 needs_history 布尔，不夹带 event_ids / time_range
2. 系统提示放判定规则，用户消息只带问题文本
"""


from app.shared.graphs.nodes.prompts.system import NEEDS_HISTORY_SYSTEM_PROMPT


def build_needs_history_system_prompt() -> str:
    """
    构建「是否需要喂养历史」的系统提示词。

    业务逻辑：
    引导模型宽松判断；要求严格 JSON，便于解析失败时走默认 true。
    """
    return NEEDS_HISTORY_SYSTEM_PROMPT


def build_needs_history_user_message(user_text: str) -> str:
    """
    构建门禁用户消息。

    Args:
        user_text: 家长本轮问题或 user_input

    Returns:
        用户消息字符串
    """
    return f"""
用户问题："{user_text}"

请判断是否需要喂养历史。只输出 JSON。
"""

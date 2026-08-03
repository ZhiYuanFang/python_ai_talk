"""
是否需要喂养历史：门禁提示词

业务说明：
在 judge_data_requirement（范围）之前，先判断回答是否需要参考喂养历史记录。
宽松策略：可能有用就 true；仅纯闲聊/与宝宝近期记录无关的通用知识才 false。

设计思路：
1. 只输出 needs_history 布尔，不夹带 event_ids / time_range
2. 系统提示放判定规则，用户消息只带问题文本
"""


def build_needs_history_system_prompt() -> str:
    """
    构建「是否需要喂养历史」的系统提示词。

    业务逻辑：
    引导模型宽松判断；要求严格 JSON，便于解析失败时走默认 true。
    """
    return """
你是家长喂养陪伴场景的数据助手。
请判断：回答用户这句话时，是否可能需要参考该宝宝的喂养历史记录（吃奶、睡觉、尿布等）。

输出格式（只返回 JSON）：
{"needs_history": true}

判定（宽松，宁可多拉）：
- true：查记录/上次/什么时候；总结/趋势/最近几天；抱怨近期模式（总醒、吃得少）；喂养相关建议有近况记录会答得更好
- false：纯闲聊、情绪倾诉且无喂养语境、与该宝宝近期记录无关的通用知识

注意事项：
1. 拿不准就 true
2. 只返回 JSON，不要解释文字
"""


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

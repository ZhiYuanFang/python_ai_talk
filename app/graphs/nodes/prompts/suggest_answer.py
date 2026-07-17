"""
suggest 意图建议生成提示词构建模块

业务说明：
构建 suggest 意图（成长建议）回答生成节点使用的系统提示词。
引导 LLM 根据历史记录、向量库知识和宝宝画像生成个性化成长建议。
复用 go_ai_talk 的 aiClinic.systemPrompt 的风格和内容框架。

设计思路：
1. 组合历史记录、向量库知识、宝宝画像作为上下文
2. 要求 LLM 给出专业、温暖、易懂的建议
3. 建议要基于数据和知识，不能凭空编造
"""

import json
from typing import Any, Dict, List


def build_suggest_answer_system_prompt() -> str:
    """
    构建 suggest 意图建议生成的系统提示词

    业务逻辑：
    引导 LLM 根据历史记录、相关知识和宝宝画像生成个性化成长建议。
    回答风格要专业、温暖、易懂，复用 go_ai_talk 的诊疗提示词风格。

    Returns:
        系统提示词字符串
    """
    return """
你是一个专业的儿科医生助手，擅长处理宝宝喂养和健康问题。
请根据提供的宝宝信息、历史记录和相关知识，为用户提供专业的成长建议。

回答要求：
1. 回答要专业、温暖、易懂，适合与家长交流
2. 建议要基于历史记录和相关知识，不要凭空编造
3. 可以从喂养规律、生长发育、注意事项等多个角度给出建议
4. 如果历史记录或知识不足，要如实说明，给出一般性建议
5. 回答要有条理，可以分点说明
6. 语气要鼓励和支持，避免让家长感到焦虑
"""


def build_suggest_answer_user_message(
    user_text: str,
    history_events: List[Dict[str, Any]],
    knowledge_results: List[Dict[str, Any]],
    baby_profile: Dict[str, Any],
) -> str:
    """
    构建 suggest 意图建议生成的用户消息

    业务逻辑：
    将用户问题、宝宝画像、历史记录和相关知识组合成用户消息。

    Args:
        user_text: 用户的问题文本
        history_events: 历史记录列表
        knowledge_results: 向量检索结果列表
        baby_profile: 宝宝画像信息

    Returns:
        用户消息字符串
    """
    # 格式化宝宝画像
    baby_info = ""
    if baby_profile:
        baby_info = f"""
宝宝信息：
- 生日：{baby_profile.get("birthday", "未知")}
- 性别：{baby_profile.get("gender", "未知")}
"""

    # 格式化历史记录（只取最近10条）
    history_info = ""
    if history_events:
        recent_events = history_events[-10:]
        history_info = f"""
最近喂养记录：
{json.dumps(recent_events, ensure_ascii=False, indent=2)}
"""

    # 格式化知识
    knowledge_info = ""
    if knowledge_results:
        knowledge_texts = [f"- {r['content']}（相似度：{r['score']}）" for r in knowledge_results]
        knowledge_info = f"""
相关知识：
{"\n".join(knowledge_texts)}
"""

    return f"""
用户问题："{user_text}"

{baby_info}

{history_info}

{knowledge_info}

请根据以上信息，为用户提供专业的成长建议。
"""

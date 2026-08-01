"""
suggest 意图建议生成提示词构建模块

业务说明：
构建 suggest 意图回答生成节点使用的系统提示词。
与 clinic/tip 统一为懂娃闺蜜口语人格，避免主对话人格分裂。

设计思路：
1. 组合历史记录、向量库知识、宝宝画像作为背景
2. 口语、鼓励，不做医生腔
"""

import json
from typing import Any, Dict, List


def build_suggest_answer_system_prompt() -> str:
    """
    构建 suggest 意图建议生成的系统提示词

    Returns:
        系统提示词字符串
    """
    return """
你是家长身边懂娃的闺蜜，不是医生。
根据宝宝信息、喂养记录和知识背景，用口语跟「你」聊聊可行的小建议。
先接住心情，再顺嘴提点实用的；别端着分点讲课，别制造焦虑。
不做诊断、不开药；真担心身体状况时，温柔提醒可以问问医生。
信息不够就老实说，别编。
"""


def build_suggest_answer_user_message(
    user_text: str,
    history_events: List[Dict[str, Any]],
    knowledge_results: List[Dict[str, Any]],
    baby_profile: Dict[str, Any],
) -> str:
    """
    构建 suggest 意图建议生成的用户消息

    Args:
        user_text: 用户的问题文本
        history_events: 历史记录列表
        knowledge_results: 向量检索结果列表
        baby_profile: 宝宝画像信息

    Returns:
        用户消息字符串
    """
    baby_info = ""
    if baby_profile:
        baby_info = f"""
宝宝信息：
- 生日：{baby_profile.get("birthday", "未知")}
- 性别：{baby_profile.get("gender", "未知")}
"""

    history_info = ""
    if history_events:
        recent_events = history_events[-10:]
        history_info = f"""
最近喂养记录：
{json.dumps(recent_events, ensure_ascii=False, indent=2)}
"""

    knowledge_info = ""
    if knowledge_results:
        knowledge_texts = [
            f"- {r['content']}（相似度：{r['score']}）" for r in knowledge_results
        ]
        knowledge_info = f"""
可参考的知识（背景）：
{"\n".join(knowledge_texts)}
"""

    return f"""
家长说："{user_text}"

{baby_info}

{history_info}

{knowledge_info}

请用闺蜜口语回复。
"""

"""
诊疗回答提示词构建模块

业务说明：
构建诊疗场景回答生成节点使用的系统提示词。
复用 go_ai_talk 的 aiClinic.systemPrompt 风格和内容框架。
支持思考模式（thinking），先输出思考过程再输出回答。

设计思路：
1. 组合宝宝画像、历史记录、向量库知识作为上下文
2. 要求 LLM 先思考再回答，模拟诊疗思路
3. 思考格式用 [思考] 标记，回答直接输出
4. 回答风格专业、温暖、易懂
"""

import json
from typing import Any, Dict, List


def build_clinic_answer_system_prompt() -> str:
    """
    构建诊疗回答的系统提示词

    业务逻辑：
    引导 LLM 作为儿科医生助手，根据宝宝信息、历史记录和相关知识提供诊疗建议。
    复用 go_ai_talk 的 aiClinic.systemPrompt 风格。
    支持思考模式：先进行思考分析，再给出回答。

    Returns:
        系统提示词字符串
    """
    return """
你是一个专业的儿科医生助手，擅长处理宝宝喂养和健康问题。

请根据宝宝信息、历史记录和相关知识，为用户提供专业的诊疗建议。
回答风格：专业、温暖、易懂。

先进行思考，然后给出详细的回答。

思考格式：[思考]你的思考过程...
回答格式：直接给出回答内容。

注意事项：
1. 建议要基于提供的历史记录和知识，不要凭空编造
2. 如果信息不足，要如实说明，建议就医或进一步观察
3. 回答要有条理，可以分点说明
4. 语气要温暖和支持，避免让家长感到焦虑
5. 不要给出具体的药物剂量或处方建议，应建议咨询医生
"""


def build_clinic_answer_user_message(
    question: str,
    history_events: List[Dict[str, Any]],
    knowledge_results: List[Dict[str, Any]],
    baby_profile: Dict[str, Any],
) -> str:
    """
    构建诊疗回答的用户消息

    业务逻辑：
    将用户问题、宝宝画像、历史记录和相关知识组合成用户消息。

    Args:
        question: 用户的诊疗问题
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
{baby_info}

{history_info}

{knowledge_info}

请根据以上信息，为用户提供专业的诊疗建议。

用户问题：{question}
"""

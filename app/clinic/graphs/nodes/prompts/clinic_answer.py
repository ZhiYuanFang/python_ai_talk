"""
陪伴回答提示词构建模块（clinic 流式）

业务说明：
构建 clinic 场景回答生成节点使用的系统提示词。
角色为对妈妈/家长说话的懂娃闺蜜：口语接情绪，喂养知识当背景。

设计思路：
1. 组合宝宝画像、历史记录、向量库知识、近期陪伴对话
2. 口语化，不做医生诊疗口吻
3. 保留不诊断、不开药、必要时温柔劝就医
"""

import json
from typing import Any, Dict, List, Optional


def build_clinic_answer_system_prompt() -> str:
    """
    构建 clinic 回答的系统提示词

    业务逻辑：
    引导 LLM 作为懂一点喂养的闺蜜，和家长口语聊天；
    先接住情绪，再顺嘴带一点实用信息；知识与记录只作背景。

    Returns:
        系统提示词字符串
    """
    return """
你是家长（妈妈/爸爸）身边懂娃的闺蜜，不是医生，也不要自称儿科助手。
用口语跟「你」聊天，称呼宝宝用「宝宝/小家伙」。主打接住对方情绪，像最好的闺蜜一样陪着说。

你可以参考喂养记录和知识库里的信息，让自己显得「懂一点」，但别端着讲课，别开医嘱。
先共情，再顺嘴给一点轻松、可做的小提醒就好。

注意事项：
1. 不要做疾病诊断，不要给药物剂量或处方
2. 家长若明显担心身体状况，用闺蜜口吻轻轻提醒：不放心就问问医生/去医院看看
3. 信息不够就诚实说，别编
4. 回答口语、自然，别用说明书标题和硬邦邦分点清单（除非家长明确要条理）
5. 不要制造焦虑

若开启思考：可用 [思考]... 再给出回答；回答正文直接口语说。
"""


def build_clinic_answer_user_message(
    question: str,
    history_events: List[Dict[str, Any]],
    knowledge_results: List[Dict[str, Any]],
    baby_profile: Dict[str, Any],
    chat_context: Optional[str] = None,
) -> str:
    """
    构建 clinic 回答的用户消息

    业务逻辑：
    将用户问题、宝宝画像、喂养历史、知识与近期陪伴对话组合成用户消息。
    chat_context 与喂养历史分离，仅作续聊记忆。

    Args:
        question: 家长本轮问题
        history_events: 喂养历史记录列表
        knowledge_results: 向量检索结果列表
        baby_profile: 宝宝画像信息
        chat_context: 近期 tip/clinic 陪伴对话文本（可选）

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
最近喂养记录（背景，不是聊天记录）：
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

    chat_block = ""
    if chat_context and chat_context.strip():
        chat_block = f"\n{chat_context.strip()}\n"

    return f"""
{baby_info}

{history_info}

{knowledge_info}
{chat_block}
请用闺蜜口语回家长。家长说：{question}
"""

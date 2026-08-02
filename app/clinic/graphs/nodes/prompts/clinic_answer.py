"""
陪伴回答提示词构建模块（clinic 流式）

业务说明：
构建 clinic 场景回答生成节点使用的系统提示词。
角色为对妈妈/家长说话的懂娃闺蜜：口语接情绪；查记录题按喂养史答时间。

设计思路：
1. 组合宝宝画像、精简历史、向量库知识、近期陪伴对话
2. 查记录题优先事实时间；闲聊题保持短口语
3. 保留不诊断、不开药、必要时温柔劝就医
"""

import json
from typing import Any, Dict, List, Optional

from app.shared.history_prompt_fields import slim_history_events_for_prompt


def build_clinic_answer_system_prompt() -> str:
    """
    构建 clinic 回答的系统提示词。
    """
    return """
你是家长（妈妈/爸爸）身边懂娃的闺蜜，不是医生，也不要自称儿科助手。
用口语跟「你」聊天，称呼宝宝用「宝宝/小家伙」。

【查记录题】若家长在问上次/上一次/什么时候/何时/分别何时等：
1. 必须以「喂养记录」为准回答，不要编造时间
2. 问单一事件上次：说出该事件最近一条的时间（优先 startTime，没有再用 endTime）
3. 问多个事件「分别」：按事件类型各取最近一条，分别说清
4. 记录里没有就老实说没记到
5. 这类题可以略长一点把时间说清楚，不受下面约 50 字限制

【闲聊/建议题】：
先共情，再顺嘴给一点轻松、可做的小提醒；知识与记录只作背景。
回复控制在大约 50 字内，关键字可加粗，可适度用表情。

注意事项：
1. 不要做疾病诊断，不要给药物剂量或处方
2. 家长若明显担心身体状况，轻轻提醒：不放心就问问医生
3. 信息不够就诚实说，别编
4. 别用说明书标题和硬邦邦分点清单（除非家长明确要条理）
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
    构建 clinic 回答的用户消息（历史已裁剪字段）。
    """
    baby_info = ""
    if baby_profile:
        baby_info = f"""
宝宝信息：
- 生日：{baby_profile.get("birthday", "未知")}
- 性别：{baby_profile.get("gender", "未知")}
"""

    history_info = ""
    slim = slim_history_events_for_prompt(history_events)
    if slim:
        # 查记录题用最近若干条即可
        recent_events = slim[-20:]
        history_info = f"""
喂养记录（答题依据；不是聊天记录）：
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

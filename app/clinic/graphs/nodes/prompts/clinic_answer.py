"""
陪伴回答提示词构建模块（clinic 流式）

业务说明：
构建 clinic 场景回答生成节点使用的系统提示词。
查记录：点查念可读时间；汇总据记录谈变化。
"""

import json
from typing import Any, Dict, List, Optional

from app.shared.history_prompt_fields import (
    build_daily_history_summary,
    looks_like_summary_query,
    slim_history_events_for_prompt,
)


def build_clinic_answer_system_prompt() -> str:
    """构建 clinic 回答的系统提示词。"""
    return """
你是家长（妈妈/爸爸）身边懂娃的闺蜜，不是医生，也不要自称儿科助手。
用口语跟「你」聊天，称呼宝宝用「宝宝/小家伙」。

【点查时间题】若问上次/上一次/什么时候/何时开始/分别何时：
1. 必须以喂养记录为准，不要编造
2. 直接念记录里的 startTime（可读中文时间）；没有再用 endTime
3. 多事件「分别」：各类型取最近一条，分别说清
4. 没有对应记录就老实说没记到
5. 禁止只说「前两天/最近」等模糊话；必须说出注入的可读时间
6. 可略长，不受约 50 字限制

【汇总题】若问最近N天/总结/变化/趋势：
1. 优先参考「按日汇总」，再结合明细
2. 用次数、总量等有数的信息说变化；没数别编
3. 数据不够就老实说记得不多
4. 可略长，把趋势说清楚

【闲聊/建议题】：
先共情，再顺嘴给一点轻松小提醒；知识与记录只作背景。
回复约 50 字内，可加粗关键字，可适度用表情。

注意事项：
1. 不要做疾病诊断，不要给药物剂量或处方
2. 真担心身体状况，轻轻提醒问问医生
3. 信息不够就诚实说，别编
4. 不要制造焦虑

若开启思考：可用 [思考]... 再给出回答；回答正文直接口语说。
"""


def build_clinic_answer_user_message(
    question: str,
    history_events: List[Dict[str, Any]],
    knowledge_results: List[Dict[str, Any]],
    baby_profile: Dict[str, Any],
    chat_context: Optional[str] = None,
) -> str:
    """构建 clinic 用户消息：最新窗口 + 可读时间；汇总题附加按日聚合。"""
    baby_info = ""
    if baby_profile:
        baby_info = f"""
宝宝信息：
- 生日：{baby_profile.get("birthday", "未知")}
- 性别：{baby_profile.get("gender", "未知")}
"""

    is_summary = looks_like_summary_query(question or "")
    time_style = "calendar" if is_summary else "relative"
    # 汇总多给一些；点查 20 条足够
    limit = 80 if is_summary else 20
    slim = slim_history_events_for_prompt(
        history_events, limit=limit, time_style=time_style
    )

    summary_block = ""
    if is_summary:
        daily = build_daily_history_summary(history_events)
        if daily:
            summary_block = f"\n{daily}\n"

    history_info = ""
    if slim:
        history_info = f"""
喂养记录明细（答题依据；时间为已转换的可读文案，请直接念给家长听）：
{json.dumps(slim, ensure_ascii=False, indent=2)}
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
{summary_block}
{history_info}
{knowledge_info}
{chat_block}
请用闺蜜口语回家长。若是查时间/汇总题，必须以记录为准。家长说：{question}
"""

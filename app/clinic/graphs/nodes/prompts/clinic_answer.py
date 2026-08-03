"""
陪伴回答提示词构建模块（clinic 流式）

业务说明：
构建 clinic 场景回答生成节点使用的系统提示词。
查记录：点查念可读时间；汇总据记录谈变化。
建议/闲聊：有经验闺蜜口吻，有对话或喂养史则点名依据再答，约 50 字。
"""

import json
from typing import Any, Dict, List, Optional

from app.shared.baby_age import format_age_months_text
from app.shared.history_prompt_fields import (
    build_daily_history_summary,
    looks_like_summary_query,
    slim_history_events_for_prompt,
)


def build_clinic_answer_system_prompt() -> str:
    """构建 clinic 回答的系统提示词。"""
    return """
你是家长（妈妈/爸爸）身边带过娃、听过很多吐槽的闺蜜，不是医生，也不要自称儿科助手。
用口语跟「你」聊天，称呼宝宝用「宝宝/小家伙」。
态度：先接情绪 → 点出依据（上次聊过的或喂养记录）→ 再轻轻一句提醒；不端着、不科普腔、不装懂。

【有据必点名】
1. 下方若有「近期陪伴对话」：正文必须点到上次相关一句（可意译），再答本轮；禁止当首轮冷启动。
2. 下方若有「喂养记录」：正文必须点到与本轮最相关的 1 条事实（时间/次数/间隔等），再对应回应；禁止只共情不碰数据、禁止堆砌多条。
3. 对话与记录都没有：禁止编造「上次你说」「记录里」；可短陪，诚实即可。
4. 口述与记录不一致时：以记录为准，用口语圆一下。

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
按「有据必点名」作答；回复约 50 字内（含点名那一句），可加粗关键字，可适度用表情。
通用知识仅作轻背景，不得替代对话或记录成为「假记忆」。

注意事项：
1. 不要做疾病诊断，不要给药物剂量或处方
2. 真担心身体状况，轻轻提醒问问医生
3. 信息不够就诚实说，别编
4. 不要制造焦虑

若开启思考：可用 [思考]... 再给出回答；回答正文直接口语说。
"""


def _clinic_closing_instruction(
    *,
    has_history: bool,
    has_chat: bool,
    is_summary: bool,
    question: str,
) -> str:
    """按是否有记录/对话拼接收尾硬约束。"""
    parts: List[str] = []
    if is_summary or looks_like_summary_query(question or ""):
        parts.append("若是查时间/汇总题，必须以记录为准，可略长念清。")
    else:
        parts.append("若是查时间题，必须以记录为准，可略长念清。")

    if has_chat:
        parts.append("必须结合近期陪伴对话，点名上次相关内容再答本轮。")
    if has_history:
        parts.append("必须结合喂养记录，点名 1 条相关事实再回应。")
    if not has_chat and not has_history:
        parts.append("没有对话和记录时，不要编造「上次」或「记录里」。")

    if not (is_summary or _looks_like_time_query(question or "")):
        parts.append("闲聊/建议约 50 字内。")

    parts.append(f"用有经验闺蜜口语回家长。家长说：{question}")
    return "".join(parts)


def _looks_like_time_query(question: str) -> bool:
    """粗判点查时间题（与 system 点查规则对齐的轻量启发）。"""
    q = question or ""
    keys = ("上次", "上一次", "什么时候", "何时", "几点", "哪天")
    return any(k in q for k in keys)


def build_clinic_answer_user_message(
    question: str,
    history_events: List[Dict[str, Any]],
    knowledge_results: List[Dict[str, Any]],
    baby_profile: Dict[str, Any],
    chat_context: Optional[str] = None,
    baby_age_months: Optional[int] = None,
) -> str:
    """构建 clinic 用户消息：最新窗口 + 可读时间；汇总题附加按日聚合。"""
    baby_info = ""
    if baby_profile or baby_age_months is not None:
        age_text = format_age_months_text(baby_age_months)
        gender = (baby_profile or {}).get("gender", "未知")
        baby_info = f"""
宝宝信息：
- 月龄：{age_text}
- 性别：{gender}
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
喂养记录明细（答题依据；时间为已转换的可读文案，请直接念给家长听；回应时须点名其中 1 条相关事实）：
{json.dumps(slim, ensure_ascii=False, indent=2)}
"""

    knowledge_info = ""
    if knowledge_results:
        knowledge_texts = [
            f"- {r['content']}（相似度：{r['score']}）" for r in knowledge_results
        ]
        knowledge_info = f"""
可参考的知识（轻背景，不得编造为「记录」或「上次说过」）：
{"\n".join(knowledge_texts)}
"""

    chat_block = ""
    has_chat = bool(chat_context and chat_context.strip())
    if has_chat:
        chat_block = f"\n{chat_context.strip()}\n"

    closing = _clinic_closing_instruction(
        has_history=bool(slim),
        has_chat=has_chat,
        is_summary=is_summary,
        question=question,
    )

    return f"""
{baby_info}
{summary_block}
{history_info}
{knowledge_info}
{chat_block}
{closing}
"""

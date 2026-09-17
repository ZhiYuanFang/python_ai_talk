"""
陪伴回答提示词构建模块（clinic 流式）

业务说明：
构建 clinic 场景回答生成节点使用的系统提示词。
人设为育儿专家（非医生）。按 needs_history 分叉：
- 需要史：有喂养记录则必点 1 条相关事实；chat_context 可参考、不强制点名
- 不需要史：不注入记录/对话块，禁止编造本机记忆；不征求肯定
"""

import json
from typing import Any, Dict, List, Optional

from app.clinic.graphs.nodes.prompts.system import (
    CLINIC_ANSWER_SYSTEM_PROMPT_WITH_HISTORY,
    CLINIC_ANSWER_SYSTEM_PROMPT_WITHOUT_HISTORY,
)
from app.shared.baby_age import format_age_months_text
from app.shared.graphs.state_patch import state_get
from app.shared.history_prompt_fields import (
    build_daily_history_summary,
    looks_like_summary_query,
    slim_history_events_for_prompt,
)


def resolve_clinic_needs_history(state: Any) -> bool:
    """
    从 clinic state 解析本轮是否按「需要喂养史」模式生成提示词。

    Args:
        state: 图 State（Pydantic 或 dict）；字段经 state_get 读取。

    force_needs_history 优先为 True；needs_history 缺省按 True（保守走有据路径）。
    """
    if state_get(state, "force_needs_history"):
        return True
    needs = state_get(state, "needs_history")
    if needs is None:
        return True
    return bool(needs)


def build_clinic_answer_system_prompt(*, needs_history: bool = True) -> str:
    """
    构建 clinic 回答的系统提示词。

    Args:
        needs_history: True 保留记录必点与点查/汇总规则；False 关闭史依据
    """
    if needs_history:
        return CLINIC_ANSWER_SYSTEM_PROMPT_WITH_HISTORY
    return CLINIC_ANSWER_SYSTEM_PROMPT_WITHOUT_HISTORY


def _clinic_closing_instruction(
    *,
    needs_history: bool,
    has_history: bool,
    has_chat: bool,
    is_summary: bool,
    question: str,
    baby_age_months: Optional[int] = None,
) -> str:
    """按 needs_history 与是否有记录拼接收尾硬约束（对话非必点；无征求肯定）。"""
    parts: List[str] = []
    if needs_history:
        if is_summary or looks_like_summary_query(question or ""):
            parts.append("若是查时间/汇总题，必须以记录为准，先念清事实。")
        else:
            parts.append("若是查时间题，必须以记录为准，先念清事实。")
        if has_history:
            parts.append("必须结合喂养记录，点名 1 条相关事实再回应。")
        else:
            parts.append("没有喂养记录时，不要编造「记录里」。")
        if has_chat:
            parts.append("近期对话仅可参考，不必点名「上次」；勿编造未提供的对话。")
    else:
        parts.append(
            "本轮不需要喂养史与陪伴对话依据；不要点名「上次你说」或「记录里」，不要编造本机事实。"
        )

    if baby_age_months is not None:
        parts.append("月龄已知，回答可结合该月龄，勿编造未提供的记录。")
    else:
        parts.append("月龄未知时不要假设具体月龄。")

    parts.append("约 80 字内。用育儿专家口吻回家长。")
    parts.append(f"家长说：{question}")
    return "".join(parts)


def build_clinic_answer_user_message(
    question: str,
    history_events: List[Dict[str, Any]],
    baby_profile: Dict[str, Any],
    chat_context: Optional[str] = None,
    baby_age_months: Optional[int] = None,
    *,
    needs_history: bool = True,
) -> str:
    """
    构建 clinic 用户消息。

    needs_history=False 时不注入喂养记录块与 chat_context 块。
    有记录则标注必点；有对话仅作可选背景。不再注入通识「知识库参考」。
    """
    baby_info = ""
    if baby_profile or baby_age_months is not None:
        age_text = format_age_months_text(baby_age_months)
        gender = (baby_profile or {}).get("gender", "未知")
        baby_info = f"""
宝宝信息：
- 月龄：{age_text}
- 性别：{gender}
"""

    summary_block = ""
    history_info = ""
    chat_block = ""
    has_chat = False
    slim: List[Dict[str, Any]] = []

    if needs_history:
        is_summary = looks_like_summary_query(question or "")
        time_style = "calendar" if is_summary else "relative"
        # 汇总多给一些；点查 20 条足够
        limit = 80 if is_summary else 20
        slim = slim_history_events_for_prompt(
            history_events, limit=limit, time_style=time_style
        )

        if is_summary:
            daily = build_daily_history_summary(history_events)
            if daily:
                summary_block = f"\n{daily}\n"

        if slim:
            history_info = f"""
喂养记录明细（答题依据；时间为已转换的可读文案；回应时须点名其中 1 条相关事实）：
{json.dumps(slim, ensure_ascii=False, indent=2)}
"""

        has_chat = bool(chat_context and chat_context.strip())
        if has_chat:
            chat_block = f"""
近期陪伴对话（可选背景，不必点名「上次」；勿编造未出现内容）：
{chat_context.strip()}
"""
    else:
        is_summary = False

    closing = _clinic_closing_instruction(
        needs_history=needs_history,
        has_history=bool(slim),
        has_chat=has_chat,
        is_summary=is_summary,
        question=question,
        baby_age_months=baby_age_months,
    )

    return f"""
{baby_info}
{summary_block}
{history_info}
{chat_block}
{closing}
"""

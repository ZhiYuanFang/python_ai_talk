"""
小贴士（事件开场）回答提示词构建模块

业务说明：
事件添加后 tip 先开口：有经验闺蜜对家长说几句口语暖话。
有近史/近期对话则点名依据；约 50 字；无据不编。
可与 clinic 共享陪伴会话，后续由 clinic 续聊。
"""

import json
import time
from typing import Any, Dict, List, Optional

from app.shared.history_prompt_fields import slim_history_events_for_prompt
from app.tip.graphs.nodes.derive_baby_age import shanghai_now


def build_tip_answer_system_prompt() -> str:
    """
    构建 tip 回答的系统提示词

    Returns:
        系统提示词字符串
    """
    return """
你是家长身边带过娃的闺蜜。刚才家长记了一条宝宝相关事件，你先开口陪两句。
口语、短一点、暖一点，像微信里随口回的消息，别写成「注意事项清单」。
态度：接住当下 → 若有近况或上次聊过的就点一句 → 再轻轻提接下来留意啥。
有「近期喂养记录」时：必须点名 1 条相关近况，再对应开口；禁止空喊加油。
有「近期陪伴对话」时：必须接上上次相关一句，再谈本条事件。
没有记录也没有对话时：禁止编造「上次/记录里」；可短暖一句。
全文约 50 字内；别端着、别诊断、别开药。
月龄若是「未知」，别假设是新生儿。
真担心身体状况时，用闺蜜口吻轻轻说不放心就问问医生。
"""


def format_tip_age_text(baby_age_months: Optional[int]) -> str:
    """
    将内部月龄表示转为提示词文案。

    业务逻辑：
    - None → 「宝宝月龄：未知」
    - 非负整数（含算出的 0）→ 「宝宝月龄：{n} 个月」

    Args:
        baby_age_months: 自算月龄，或 None 表示未知

    Returns:
        提示词用月龄行
    """
    if baby_age_months is None:
        return "宝宝月龄：未知"
    return f"宝宝月龄：{baby_age_months} 个月"


def _tip_closing_instruction(
    event_name: str,
    *,
    has_history: bool,
    has_chat: bool,
) -> str:
    """按是否有记录/对话拼接收尾硬约束。"""
    parts: List[str] = [f"请针对「{event_name}」用有经验闺蜜口语跟家长说一小段。"]
    if has_chat:
        parts.append("必须结合近期陪伴对话，点名上次相关内容。")
    if has_history:
        parts.append("必须结合近期喂养记录，点名 1 条近况。如果喂养记录的时间距今超过2天，用「之前有一次/上次看到」来引导，不要说成「现在/今天」，避免让家长觉得你在拿旧事说现在。")
    if not has_chat and not has_history:
        parts.append("没有对话和记录时，不要编造「上次」或「记录里」。")
    parts.append("大约50字内，别用强制标题结构，关键字加粗，可适度用表情。")
    return "".join(parts)


def build_tip_answer_user_message(
    event_info: Dict[str, Any],
    baby_age_months: Optional[int],
    history_events: List[Dict[str, Any]],
    knowledge_results: List[Dict[str, Any]],
    baby_profile: Dict[str, Any],
    chat_context: Optional[str] = None,
) -> str:
    """
    构建 tip 回答的用户消息

    Args:
        event_info: 触发事件信息，包含 event_id 和 event_name
        baby_age_months: 自算月龄；None 表示未知
        history_events: 近期喂养历史记录列表
        knowledge_results: 向量检索结果列表
        baby_profile: 宝宝画像信息
        chat_context: 近期陪伴对话（可选）

    Returns:
        用户消息字符串
    """
    event_name = event_info.get("event_name", "未知事件")
    event_id = event_info.get("event_id", "")
    event_info_text = f"""
当前触发事件：
- 事件名称：{event_name}
- 事件ID：{event_id}
"""

    now = shanghai_now()
    local_str = now.strftime("%Y-%m-%d %H:%M:%S")
    unix_sec = int(time.time())
    age_line = format_tip_age_text(baby_age_months)
    time_age_text = f"""
当前时间：{local_str}（Asia/Shanghai）
当前时间 Unix 秒：{unix_sec}
{age_line}
"""

    baby_info = ""
    if baby_profile:
        baby_info = f"""
宝宝信息：
- 生日：{baby_profile.get("birthday", "未知")}
- 性别：{baby_profile.get("sex") or baby_profile.get("gender", "未知")}
"""

    history_info = ""
    recent_events: List[Dict[str, Any]] = []
    if history_events:
        recent_events = slim_history_events_for_prompt(
            history_events, limit=5, time_style="relative"
        )
        history_info = f"""
近期喂养记录（回应时须点名其中 1 条相关近况）：
{json.dumps(recent_events, ensure_ascii=False, indent=2)}
"""

    knowledge_info = ""
    if knowledge_results:
        knowledge_texts = [f"- {r['content']}" for r in knowledge_results]
        knowledge_label = (
            "知识库参考（同月龄宝宝，轻背景）"
            if baby_age_months is not None
            else "知识库参考（不限月龄，轻背景）"
        )
        knowledge_info = f"""
{knowledge_label}：
{"\n".join(knowledge_texts)}
"""

    chat_block = ""
    has_chat = bool(chat_context and chat_context.strip())
    if has_chat:
        chat_block = f"\n{chat_context.strip()}\n"

    closing = _tip_closing_instruction(
        event_name,
        has_history=bool(recent_events),
        has_chat=has_chat,
    )

    return f"""
{event_info_text}

{time_age_text}

{baby_info}

{history_info}

{knowledge_info}
{chat_block}
{closing}
"""

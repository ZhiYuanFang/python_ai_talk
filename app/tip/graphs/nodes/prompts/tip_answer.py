"""
小贴士（事件开场）回答提示词构建模块

业务说明：
事件添加后 tip 先开口：懂娃闺蜜对家长说几句口语暖话。
可与 clinic 共享陪伴会话，后续由 clinic 续聊。

设计思路：
1. 结合当前触发事件、时间、月龄、喂养史与知识背景
2. 篇幅精炼，适合卡片展示，但不强制说明书标题结构
3. 注入近期陪伴对话（若有）便于一条线续聊
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
你是家长身边懂娃的闺蜜。刚才家长记了一条宝宝相关事件，你先开口陪两句。
口语、短一点、暖一点，像微信里随口回的消息，别写成「注意事项清单」。
可以轻轻提一句接下来留意啥，但别端着、别诊断、别开药。
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
    if history_events:
        recent_events = slim_history_events_for_prompt(history_events)[-5:]
        history_info = f"""
近期喂养记录（背景）：
{json.dumps(recent_events, ensure_ascii=False, indent=2)}
"""

    knowledge_info = ""
    if knowledge_results:
        knowledge_texts = [f"- {r['content']}" for r in knowledge_results]
        knowledge_label = (
            "知识库参考（同月龄宝宝）"
            if baby_age_months is not None
            else "知识库参考（不限月龄）"
        )
        knowledge_info = f"""
{knowledge_label}：
{"\n".join(knowledge_texts)}
"""

    chat_block = ""
    if chat_context and chat_context.strip():
        chat_block = f"\n{chat_context.strip()}\n"

    return f"""
{event_info_text}

{time_age_text}

{baby_info}

{history_info}

{knowledge_info}
{chat_block}
请针对「{event_name}」用闺蜜口语跟家长说一小段（大约50字内，别用强制标题结构，关键字加粗，要善于使用表情符号）。
"""

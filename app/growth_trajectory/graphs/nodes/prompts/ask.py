"""ask 用户消息：生成下一问。"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def build_ask_user_message(
    *,
    horizon_days: int,
    baby_age_months: Optional[int],
    baby_profile: Dict[str, Any],
    qa_so_far: List[Dict[str, Any]],
    structured_round: int,
    max_structured_rounds: int,
    plan_reason: str = "",
) -> str:
    """组装补问生成用户消息。"""
    age = "未知" if baby_age_months is None else f"{baby_age_months} 个月"
    profile_json = json.dumps(baby_profile or {}, ensure_ascii=False)
    qa_json = json.dumps(qa_so_far or [], ensure_ascii=False)
    return f"""任务：生成下一道结构化问题，用于补齐未来 {horizon_days} 天成长轨迹所需信息。
当前结构化轮次：{structured_round}/{max_structured_rounds}。
规划理由：{plan_reason or "（无）"}
宝宝月龄：{age}
宝宝画像 JSON：
{profile_json}
已完成问答 JSON：
{qa_json}

请只输出一个 JSON 对象：
{{
  "id": "短 id",
  "prompt": "给家长的问题文案",
  "format": "choice" | "free_text",
  "choices": ["选项A", "选项B"]
}}
规则：format=choice 时 choices 必须恰好 2 个；format=free_text 时 choices=[]。
"""

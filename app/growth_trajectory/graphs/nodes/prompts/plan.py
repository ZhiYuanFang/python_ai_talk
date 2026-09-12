"""plan_next 用户消息：决策 enough|ask|reconfirm。"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def build_plan_user_message(
    *,
    horizon_days: int,
    baby_age_months: Optional[int],
    baby_profile: Dict[str, Any],
    history_events: List[Dict[str, Any]],
    prior_feedback: List[Any],
    qa_so_far: List[Dict[str, Any]],
    structured_round: int,
    max_structured_rounds: int,
) -> str:
    """组装规划任务用户消息（仅任务与 JSON schema）。"""
    age = "未知" if baby_age_months is None else f"{baby_age_months} 个月"
    hist_n = len(history_events or [])
    profile_json = json.dumps(baby_profile or {}, ensure_ascii=False)
    prior_json = json.dumps(prior_feedback or [], ensure_ascii=False)
    qa_json = json.dumps(qa_so_far or [], ensure_ascii=False)
    return f"""任务：决定下一步。
当前结构化轮次：{structured_round}/{max_structured_rounds}（confirm_prior 不计）。
预测窗口：未来 {horizon_days} 天。
宝宝月龄：{age}
宝宝画像 JSON：
{profile_json}
近期喂养事件条数：{hist_n}（详情可弱参考，条数少则勿强依赖）
历史反馈 JSON：
{prior_json}
已完成问答 JSON：
{qa_json}

请只输出一个 JSON 对象：
{{
  "decision": "enough" | "ask" | "reconfirm",
  "reason": "简短中文理由",
  "question": {{
    "id": "短 id",
    "prompt": "给家长的问题文案",
    "format": "choice" | "free_text",
    "choices": ["选项A", "选项B"]
  }}
}}
规则：
- decision=enough 时可省略 question。
- decision=ask|reconfirm 时必须给 question。
- format=choice 时 choices 必须恰好 2 个中文选项；format=free_text 时 choices 可为 []。
- reconfirm 仅在上一答可能选错/矛盾时使用，勿滥用。
- 若信息已够支撑 {horizon_days} 天轨迹，选 enough。
"""

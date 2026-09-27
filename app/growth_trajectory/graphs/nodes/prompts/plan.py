"""plan_next 用户消息：决策 enough|ask|reconfirm。"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.shared.feeding_history_compact import build_feeding_history_prompt_blocks


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
    # 与 generate 同一套聚合形态，避免规划与生成所见史不一致
    history_text, _legend = build_feeding_history_prompt_blocks(history_events)
    profile_json = json.dumps(baby_profile or {}, ensure_ascii=False)
    prior_json = json.dumps(prior_feedback or [], ensure_ascii=False)
    qa_json = json.dumps(qa_so_far or [], ensure_ascii=False)
    return f"""任务：决定下一步（为最终「有序可能变化阶梯」收集依据）。
当前结构化轮次：{structured_round}/{max_structured_rounds}（confirm_prior 不计）。
预测窗口：未来 {horizon_days} 天。
宝宝月龄：{age}
宝宝画像 JSON：
{profile_json}
近期喂养记录（按日聚合；可空，空则勿强依赖）：
{history_text}
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
- 补问优先摸清「当前能力边界」：会什么/不会什么、扶站是否稳、有无迈步意图、兴趣与环境等，以便排出 {horizon_days} 日内最可能的邻近变化阶梯。
- 需要家长细述时用 format=free_text（choices 可为 []）；仅二元确认时用 choice，且 choices 必须恰好 2 个中文选项。
- decision=enough 时可省略 question；enough 只表示结构化问答可结束，系统仍会再问一次自由补充，你不要假设已经生成。
- decision=ask|reconfirm 时必须给 question。
- reconfirm 仅在上一答可能选错/矛盾时使用，勿滥用。
- 若尚未摸清当前里程碑/能力边界，不要选 enough。
"""

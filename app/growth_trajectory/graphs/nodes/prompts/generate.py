"""generate 用户消息：产出有序可能变化主段的 Markdown（禁日历日主结构）。"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.shared.feeding_history_compact import build_feeding_history_prompt_blocks


def build_generate_user_message(
    *,
    horizon_days: int,
    baby_age_months: Optional[int],
    baby_profile: Dict[str, Any],
    history_events: List[Dict[str, Any]],
    prior_feedback: List[Any],
    qa_so_far: List[Dict[str, Any]],
) -> str:
    """组装最终 Markdown 生成用户消息。"""
    age = "未知" if baby_age_months is None else f"{baby_age_months} 个月"
    # 弱史：共享紧凑聚合；空则「（无）」，生成侧弱化喂养段
    history_text, _legend = build_feeding_history_prompt_blocks(history_events)
    profile_json = json.dumps(baby_profile or {}, ensure_ascii=False)
    prior_json = json.dumps(prior_feedback or [], ensure_ascii=False)
    qa_json = json.dumps(qa_so_far or [], ensure_ascii=False)
    return f"""任务：生成未来 {horizon_days} 天的成长轨迹预测 Markdown（给家长阅读）。
宝宝月龄：{age}
宝宝画像 JSON：
{profile_json}
近期喂养记录（按日聚合；可空，空则弱化喂养段）：
{history_text}
历史反馈 JSON：
{prior_json}
问答 JSON：
{qa_json}

请只输出 Markdown。必须多用 emoji 提升可读性。篇幅约 400～600 字。
禁止使用「第1天」「第2天」…「第{horizon_days}天」或按日日程作为主要分节。
必须以「有序可能变化」为主段（编号阶梯，每条写可观察行为；按发展先后或更可能先出现排序）。
示例思路（勿照抄）：若已会站 → 1.缠着人要站/要扶 2.扶物站稳或巡航 3.尝试迈步。
建议结构：
## 🌟 未来{horizon_days}天可能发生的变化
（主段：至少 2～4 条有序编号；结合问答摸清的当前能力边界，写最可能的邻近变化）
## ⚠️ 这几天需要注意什么
（辅段：安全、互动、作息等短要点）
## 🍼 结合近期喂养
（有数据则短建议；无数据则弱化并说明依据不足）
## 💛 小结
（一句鼓励）

缺喂养记录时不要编造具体喂养次数/毫升；可写观察与作息建议。
避免恐吓与绝对化医疗结论。
"""

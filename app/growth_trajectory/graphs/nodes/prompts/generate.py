"""generate 用户消息：产出 7 天整段 Markdown（禁止按日拆分）。"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


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
    # 弱史：只给少量摘要，避免空史时硬编
    hist_preview = (history_events or [])[:20]
    profile_json = json.dumps(baby_profile or {}, ensure_ascii=False)
    hist_json = json.dumps(hist_preview, ensure_ascii=False)
    prior_json = json.dumps(prior_feedback or [], ensure_ascii=False)
    qa_json = json.dumps(qa_so_far or [], ensure_ascii=False)
    return f"""任务：生成未来 {horizon_days} 天的成长轨迹预测 Markdown（给家长阅读）。
宝宝月龄：{age}
宝宝画像 JSON：
{profile_json}
近期喂养事件（可空，空则弱化喂养段）：
{hist_json}
历史反馈 JSON：
{prior_json}
问答 JSON：
{qa_json}

请只输出 Markdown。必须多用 emoji 提升可读性。
禁止使用「第1天」「第2天」…「第{horizon_days}天」或按日日程作为主要分节。
建议结构：
## 🌟 未来{horizon_days}天可能发生什么
（2～5 条可观察的变化，结合当前能力边界）
## ⚠️ 这几天需要注意什么
（安全、互动、作息等可执行注意点——本段是主体）
## 🍼 结合近期喂养
（有数据则给建议；无数据则弱化并说明依据不足）
## 💛 小结
（一句鼓励）

缺喂养记录时不要编造具体喂养次数/毫升；可写观察与作息建议。
避免恐吓与绝对化医疗结论。
"""

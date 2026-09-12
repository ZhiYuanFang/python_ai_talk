"""generate 用户消息：产出 7 天 Markdown。"""

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

请只输出 Markdown，建议结构：
# 未来{horizon_days}天成长轨迹
## 总览
（2～4 句）
## 按日建议
### 第1天
...
### 第{horizon_days}天
## 温馨提示
（非医疗诊断声明 + 可执行提醒）

缺喂养记录时不要编造具体喂养次数/毫升；可写观察与作息建议。
"""

"""confirm_prior 用户消息：基于历史反馈确认。"""

from __future__ import annotations

import json
from typing import Any, List


def build_confirm_user_message(*, prior_feedback: List[Any]) -> str:
    """组装历史反馈确认问。"""
    prior_json = json.dumps(prior_feedback or [], ensure_ascii=False)
    return f"""任务：根据家长上次轨迹反馈，生成一道确认题（不计入后续 6 轮结构化提问）。
历史反馈 JSON：
{prior_json}

请只输出一个 JSON 对象：
{{
  "id": "confirm_prior",
  "prompt": "确认文案，询问上次反馈是否仍适用",
  "format": "choice",
  "choices": ["仍然适用", "有变化，需要更新"]
}}
规则：choices 必须恰好 2 个中文选项。
"""

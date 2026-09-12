"""validate 用户消息：校验上一答是否需 reconfirm。"""

from __future__ import annotations

import json
from typing import Any, Dict, List


def build_validate_user_message(
    *,
    last_qa: Dict[str, Any],
    qa_so_far: List[Dict[str, Any]],
) -> str:
    """组装校验任务用户消息。"""
    last_json = json.dumps(last_qa or {}, ensure_ascii=False)
    qa_json = json.dumps(qa_so_far or [], ensure_ascii=False)
    return f"""任务：判断上一答是否明显矛盾/可能点错，是否需要再确认。
上一问答 JSON：
{last_json}
全部问答 JSON：
{qa_json}

请只输出一个 JSON 对象：
{{
  "need_reconfirm": true | false,
  "reason": "简短中文理由",
  "question": {{
    "id": "短 id",
    "prompt": "再确认文案",
    "format": "choice",
    "choices": ["是的，没错", "不对，我点错了"]
  }}
}}
规则：仅当 need_reconfirm=true 时必须给 question；choice 的 choices 必须恰好 2 个。
"""

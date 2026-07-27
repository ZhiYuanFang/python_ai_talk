"""
pending 澄清回复解析提示词

业务说明：
硬匹配未命中时，引导 LLM 在 pending 语境下解析用户自由文本，
返回结构化动作（confirm/select/correct/reject/new_intent/ask_again）。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List


def build_pending_reply_system_prompt() -> str:
    """澄清解析系统提示词。"""
    return """你是母婴喂养场景的澄清回复解析助手。
用户正在回答系统的澄清/消歧问句。请根据 pending 语境解析用户本句，只返回 JSON。

动作说明（action 必填，只能取下列之一）：
- confirm: 确认当前候选（仅 leaf_confirm；可带 quantity）
- select: 选中 options 中的某一项（用 event_id 或 event_name；可带 quantity）
- correct: 否定当前猜想，改到某一事件（可在 options 外；给出 event_id 或 event_name；可带 quantity）
- reject: 明确取消，不记录
- new_intent: 与澄清无关的新话题/新意图
- ask_again: 无法确定，需要再问

重要约束：
1. kind 为 parent_disambiguation 时，禁止在未指定具体子选项时使用 confirm；笼统肯定（如「是的」「好的」）必须返回 ask_again。
2. parent_disambiguation 下应优先 select（options 内）或 correct（改到具体事件）。
3. 「是的，喂了30毫升」类：leaf_confirm 用 confirm 并填 quantity；不要 new_intent。
4. 「不是的，是母乳」类：用 correct，并填写目标事件名称或 id。
5. 只返回 JSON，不要 markdown 代码块，不要解释。

JSON 格式：
{
  "action": "confirm|select|correct|reject|new_intent|ask_again",
  "event_id": "可选，select/correct 时尽量填写",
  "event_name": "可选，select/correct 时填写",
  "quantity": null
}
quantity 为数字或 null；无数量时用 null 或省略。
"""


def build_pending_reply_user_message(
    text: str,
    *,
    kind: str,
    clarify_message: str,
    original_utterance: str,
    pending_action: str,
    pending_quantity: Any,
    parent_name: str,
    options: List[Dict[str, Any]],
) -> str:
    """构建澄清解析用户消息。"""
    options_payload: List[Dict[str, Any]] = [
        {
            "event_id": o.get("event_id", ""),
            "event_name": o.get("event_name", ""),
            "extra_names": o.get("extra_names") or [],
        }
        for o in (options or [])
    ]
    context = {
        "kind": kind,
        "clarify_message": clarify_message,
        "original_utterance": original_utterance,
        "pending_action": pending_action,
        "pending_quantity": pending_quantity,
        "parent_name": parent_name,
        "options": options_payload,
        "user_reply": text,
    }
    return (
        "请解析下列 pending 澄清语境中的用户回复，只返回 JSON：\n"
        + json.dumps(context, ensure_ascii=False, indent=2)
    )

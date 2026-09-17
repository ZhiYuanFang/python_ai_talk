"""
pending 澄清回复解析提示词

业务说明：
硬匹配未命中时，引导 LLM 在 pending 语境下解析用户自由文本，
返回结构化动作（confirm/select/correct/reject/new_intent/ask_again）。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from app.feeding.graphs.nodes.prompts.system import PENDING_REPLY_SYSTEM_PROMPT


def build_pending_reply_system_prompt() -> str:
    """澄清解析系统提示词（常量见 system.py）。"""
    return PENDING_REPLY_SYSTEM_PROMPT


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

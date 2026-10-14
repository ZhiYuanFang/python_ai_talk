"""
覆盖缺口落库判定

业务说明：
仅在终局失败回复（非确认/消歧）时写入 miss inbox。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.feeding.services.agent_miss_store import agent_miss_store
from app.feeding.services.segment_outcome import OTHER_UNSUPPORTED_MSG
from app.shared.constants import TargetType

logger = logging.getLogger(__name__)


def infer_miss_fail_kind(
    *,
    content: str,
    target_type: str = "",
    need_confirm: bool = False,
) -> Optional[str]:
    """
    判定是否为应落库的终局失败；是则返回 fail_kind。

    确认/消歧中返回 None。
    """
    if need_confirm:
        return None
    text = (content or "").strip()
    if not text:
        return None
    if text.startswith("无法识别对应的事件"):
        return "event_unresolved"
    if text == OTHER_UNSUPPORTED_MSG or "暂不支持" in text:
        return "other_unsupported"
    if "估不准" in text or "暂时无法" in text:
        return "predict_uncertain"
    # other/conversation 且明确失败短句
    tt = (target_type or "").strip().lower()
    if tt in (TargetType.OTHER.value, TargetType.CONVERSATION.value):
        if "没听清" in text or "请再说" in text:
            return "segment_unclear"
    return None


def maybe_record_agent_miss(
    intent_fields: Dict[str, Any],
    *,
    user_input: str,
    device_no: str = "",
    conversation_id: str = "",
) -> Optional[str]:
    """
    若为终局失败则写入覆盖缺口。

    Side Effects:
        可能 append JSONL。
    """
    if not isinstance(intent_fields, dict):
        return None
    need_confirm = bool(intent_fields.get("need_confirm"))
    # 有 options 的消歧也不记
    if intent_fields.get("options"):
        return None
    content = str(intent_fields.get("content") or "").strip()
    # 确认话术在 confirm_message，content 可能为空或同文案
    if need_confirm or intent_fields.get("confirm_type"):
        return None
    kind = infer_miss_fail_kind(
        content=content,
        target_type=str(intent_fields.get("target_type") or ""),
        need_confirm=False,
    )
    if not kind:
        return None
    try:
        return agent_miss_store.record(
            utterance=user_input or str(intent_fields.get("utterance") or ""),
            reply=content,
            fail_kind=kind,
            device_no=device_no,
            conversation_id=conversation_id
            or str(intent_fields.get("conversation_id") or ""),
        )
    except Exception as exc:
        logger.warning("覆盖缺口落库失败: %s", exc)
        return None

"""
意图插话闸门辅助

业务说明：
封装 miss 判定与是否拼接重跑；复用 agent_miss 清单。
「数据量太少，无法预测」不在 miss 清单内，不触发拼接。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.feeding.schemas.intent import IntentResponse
from app.feeding.services.agent_miss_record import infer_miss_fail_kind
from app.feeding.services.intent_barge_store import (
    concat_anchor_and_pending,
    intent_barge_store,
)


def should_concatenate_rerun(response: IntentResponse) -> bool:
    """
    是否因 agent_miss 触发拼接重跑。

    确认/消歧不重跑；数据量太少不在 miss 清单。
    优先认 miss_fail_kind / miss_canonical_content（软回复后 content 可能已无硬词）。
    """
    if bool(response.need_confirm):
        return False
    if response.options:
        return False
    confirm_type = str(getattr(response, "confirm_type", None) or "").strip()
    if confirm_type:
        return False
    kind = str(getattr(response, "miss_fail_kind", None) or "").strip()
    if kind:
        return True
    canonical = str(getattr(response, "miss_canonical_content", None) or "").strip()
    content = canonical or str(response.content or "")
    kind2 = infer_miss_fail_kind(
        content=content,
        target_type=str(response.target_type or ""),
        need_confirm=False,
    )
    return kind2 is not None


async def maybe_prepare_concat_rerun(
    device_no: str,
    response: IntentResponse,
) -> Tuple[Optional[str], bool]:
    """
    若 miss 且有 pending 且未超轮次：拼接、清 pending、准备重跑。

    Returns:
        (concat_text, do_rerun)
    """
    if not should_concatenate_rerun(response):
        return None, False
    snap = await intent_barge_store.get_snapshot(device_no)
    if not snap.pending:
        return None, False
    if int(snap.rerun_count or 0) >= intent_barge_store.max_rerun:
        return None, False
    concat = concat_anchor_and_pending(snap.anchor_text, snap.pending)
    if not concat.strip():
        return None, False
    # 立刻清 pending 并占坑重跑
    await intent_barge_store.prepare_rerun(device_no, concat)
    return concat, True


def response_to_dump(response: IntentResponse) -> Dict[str, Any]:
    """IntentResponse → 可 JSON 的 dict。"""
    return response.model_dump()


def dump_to_response(data: Optional[Dict[str, Any]]) -> IntentResponse:
    """挂起方还原 IntentResponse；缺省合并 ack。"""
    if not data:
        return IntentResponse(
            target_type="other",
            content="已合并处理",
            need_confirm=False,
        )
    try:
        return IntentResponse.model_validate(data)
    except Exception:
        return IntentResponse(
            target_type=str(data.get("target_type") or "other"),
            content=str(data.get("content") or "已合并处理"),
            need_confirm=bool(data.get("need_confirm")),
        )

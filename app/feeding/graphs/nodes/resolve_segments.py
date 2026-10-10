"""
分句 + 段级多维节点

业务说明：
单事件跳过分句 LLM；复合句仅分句 LLM，再逐段 TYPE→EVENT→REMARK→SHAPE→QTY→TIME。
EVENT 阶梯含 extra_names / Go 备注反查；事件已定后抽明细备注。
失败引导重说，禁止回退满血 classify。
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List

from app.feeding.graphs.nodes.prompts.system import SEGMENT_SPLIT_SYSTEM_PROMPT
from app.feeding.schemas.intent_result import IntentResult
from app.feeding.services.clarification import (
    create_remark_disambiguation_pending,
    pending_to_response_fields,
)
from app.feeding.services.segment_compound import looks_like_compound
from app.feeding.services.segment_multidim import (
    drafts_to_intent,
    resolve_segment,
)
from app.shared.constants import IntentAction, IntentOp, MatchSource, TargetType
from app.shared.graphs.state_patch import state_get
from app.shared.graphs.stream_llm_collect import stream_llm_collect
from app.shared.llm_client import llm_model_config_from_mapping

logger = logging.getLogger(__name__)

_JSON_BLOCK = re.compile(r"\{[\s\S]*\}")


def _parse_split(content: str) -> Dict[str, Any]:
    """解析分句 JSON。"""
    raw = (content or "").strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = _JSON_BLOCK.search(raw)
        if not m:
            return {}
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return {}


async def _llm_split(
    text: str, llm_model: Dict[str, Any]
) -> Dict[str, Any]:
    """调用分句 LLM；失败返回空。"""
    cfg = llm_model_config_from_mapping(llm_model)
    content = await stream_llm_collect(
        messages=[
            {
                "role": "user",
                "content": f"请分句：\n{(text or '').strip()}",
            }
        ],
        model_config=cfg,
        system_prompt=SEGMENT_SPLIT_SYSTEM_PROMPT,
        node_name="resolve_segments",
    )
    return _parse_split(content or "")


async def resolve_segments(state: Any) -> Dict[str, Any]:
    """
    图入口：单事件多维或复合分句多维。

    Returns:
        intent_result / need_confirm / match_source 等
    """
    text = (state_get(state, "user_input") or state_get(state, "text") or "").strip()
    device_no = state_get(state, "device_no") or ""
    full_events = (
        state_get(state, "event_dictionary_full")
        or state_get(state, "event_dictionary")
        or []
    )
    llm_model = (
        state_get(state, "llm_model")
        or state_get(state, "model_config")
        or {}
    )
    if not isinstance(llm_model, dict):
        llm_model = {}
    conversation_id = state_get(state, "conversation_id") or None

    if not text:
        ir = {
            "target_type": TargetType.CONVERSATION.value,
            "events": [],
            "content": "没听清，请再说一遍。",
            "need_confirm": False,
        }
        return {
            "intent_result": IntentResult.model_validate(ir),
            "need_confirm": False,
            "intent_cache_hit": False,
            "match_source": MatchSource.NAME.value,
        }

    sentence_tt = ""
    segments: List[str]
    if looks_like_compound(text):
        logger.info("复合句 → 分句 LLM: %s", text[:60])
        data = await _llm_split(text, llm_model)
        segs = data.get("segments") if isinstance(data, dict) else None
        if not isinstance(segs, list) or not any(str(s).strip() for s in segs):
            logger.info("分句失败，引导重说")
            ir = {
                "target_type": TargetType.CONVERSATION.value,
                "events": [],
                "content": "没听清有几件事，请分开说一下。",
                "need_confirm": False,
                "segment_failed": True,
            }
            return {
                "intent_result": IntentResult.model_validate(ir),
                "need_confirm": False,
                "intent_cache_hit": False,
                "match_source": MatchSource.LLM.value,
            }
        segments = [str(s).strip() for s in segs if str(s).strip()]
        sentence_tt = str(data.get("target_type") or "").strip().lower()
    else:
        logger.info("单事件多维（可含明细备注 LLM）: %s", text[:60])
        segments = [text]

    # 同句备注反查短缓存，避免重复 HTTP
    remark_cache: Dict[str, List[Dict[str, Any]]] = {}
    drafts = []
    for seg in segments:
        draft = await resolve_segment(
            seg,
            utterance=text,
            full_events=full_events,
            sentence_target_type=sentence_tt,
            device_no=device_no,
            remark_cache=remark_cache,
            llm_model=llm_model,
        )
        # extra_names / Go 多命中：立即消歧 pending
        if draft.disambiguation_leaves:
            kw = draft.disambiguation_keyword or draft.remark or seg
            pending = create_remark_disambiguation_pending(
                keyword=kw,
                leaves=draft.disambiguation_leaves,
                original_utterance=text,
                action=IntentAction.ONE.value,
                quantity=None,
                match_source=MatchSource.NAME.value,
                device_no=device_no,
                model_config=llm_model,
                conversation_id=conversation_id,
                events=[],
                op=str(draft.op or IntentOp.CREATE.value),
            )
            fields = pending_to_response_fields(pending)
            logger.info(
                "段事件多命中消歧: keyword=%s options=%s",
                kw,
                len(draft.disambiguation_leaves),
            )
            return {
                "intent_result": IntentResult.model_validate(fields),
                "need_confirm": True,
                "confirm_type": fields.get("confirm_type") or "",
                "confirm_message": fields.get("confirm_message") or "",
                "conversation_id": pending.conversation_id,
                "remark": kw,
                "intent_cache_hit": False,
                "match_source": MatchSource.NAME.value,
            }
        drafts.append(draft)

    intent = drafts_to_intent(drafts, utterance=text)
    need_confirm = bool(intent.get("need_confirm"))
    # 失败重说 / 闲聊 / 退出：不需确认
    if intent.get("segment_failed") or intent.get("target_type") in (
        TargetType.CONVERSATION.value,
        TargetType.EXIT.value,
    ):
        need_confirm = False

    logger.info(
        "段多维完成: segments=%s target=%s events=%s need_confirm=%s remark=%s",
        len(segments),
        intent.get("target_type"),
        len(intent.get("events") or []),
        need_confirm,
        intent.get("remark") or "",
    )
    return {
        "intent_result": IntentResult.model_validate(intent),
        "need_confirm": need_confirm,
        "intent_cache_hit": False,
        "match_source": intent.get("match_source") or MatchSource.NAME.value,
        "match_confidence": intent.get("match_confidence"),
        "matched_vector_id": "",
        "remark": intent.get("remark") or "",
    }

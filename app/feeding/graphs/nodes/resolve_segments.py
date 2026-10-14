"""
分句 + 段级多维节点

业务说明：
单事件跳过分句与满血 classify；复合句仅分句 LLM，再逐段多维。
段序：TYPE(可小LLM) → EVENT(词典→extra_names→向量→Go→小LLM)
→ 明细备注 LLM → SHAPE(结束线索/可小LLM) → QTY(可小LLM) → TIME(可小LLM)。
失败引导重说，禁止回退满血 classify。
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.feeding.graphs.nodes.prompts.system import SEGMENT_SPLIT_SYSTEM_PROMPT
from app.feeding.schemas.intent_result import IntentResult
from app.feeding.services.clarification import (
    build_delete_confirm_message,
    build_history_confirm_message,
    build_leaf_confirm_message,
    create_leaf_confirm_pending,
    create_parent_disambiguation_pending,
    create_remark_disambiguation_pending,
    pending_to_response_fields,
)
from app.feeding.services.segment_compound import looks_like_compound
from app.feeding.services.segment_multidim import (
    SegmentDraft,
    drafts_to_intent,
    resolve_segment,
)
from app.feeding.services.segment_remark import soft_event_phrase_from_segment
from app.shared.constants import IntentAction, IntentOp, MatchSource, TargetType
from app.shared.graphs.state_patch import state_get
from app.shared.graphs.stream_llm_collect import stream_llm_collect
from app.shared.llm_client import llm_model_config_from_mapping

logger = logging.getLogger(__name__)

_JSON_BLOCK = re.compile(r"\{[\s\S]*\}")


def _is_predict_draft(draft: SegmentDraft) -> bool:
    """段是否为 R·predict。"""
    return (
        draft.target_type == TargetType.READ.value
        and (draft.read_source or "").strip().lower() == "predict"
    )


def _soft_confirm_message(draft: SegmentDraft, event_name: str) -> str:
    """
    EVENT 软候选确认话术。

    predict：复述段文并把核词换成候选事件名（如午饭→辅食）。
    """
    name = (event_name or "").strip() or "相关事件"
    text = (draft.text or "").strip()
    phrase = (draft.disambiguation_keyword or "").strip() or soft_event_phrase_from_segment(
        text
    )
    if _is_predict_draft(draft):
        if phrase and phrase in text:
            return f"你要问的是{text.replace(phrase, name, 1)}吗？"
        return f"你要问的是关于「{name}」的预计时间吗？"
    op = str(draft.op or "").strip().lower()
    if draft.target_type == TargetType.READ.value or op == IntentOp.READ.value:
        return build_history_confirm_message(name, remark="")
    if draft.target_type == TargetType.DELETE.value or op == IntentOp.DELETE.value:
        return build_delete_confirm_message(name)
    if op == "end" or (
        draft.target_type == TargetType.UPDATE.value and draft.action == IntentAction.END.value
    ):
        return f"您是要结束「{name}」吗？"
    return build_leaf_confirm_message(
        name,
        draft.action or IntentAction.ONE.value,
        op=op or IntentOp.CREATE.value,
        quantity=draft.quantity,
        start_time=draft.start_time or None,
        end_time=draft.end_time or None,
        remark=(draft.remark or "").strip(),
    )


def _soft_pending_events(
    draft: SegmentDraft, leaf: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """由段 TYPE 维与候选叶拼 pending.events（确认后执行用）。"""
    leaf = leaf or {}
    eid = str(leaf.get("event_id") or "").strip()
    ename = str(leaf.get("event_name") or "").strip()
    if _is_predict_draft(draft):
        return [
            {
                "op": "",
                "action": "",
                "event_id": eid,
                "event_name": ename,
                "quantity": None,
                "start_time": 0,
                "end_time": 0,
                "remark": (draft.remark or "").strip(),
                "segment_text": draft.text,
            }
        ]
    if draft.target_type == TargetType.READ.value:
        op_out = IntentOp.READ.value
    elif draft.op == "end":
        op_out = "end"
    elif draft.target_type == TargetType.UPDATE.value:
        op_out = IntentOp.UPDATE.value
    elif draft.target_type == TargetType.DELETE.value:
        op_out = IntentOp.DELETE.value
    else:
        op_out = draft.op or IntentOp.CREATE.value
    return [
        {
            "op": op_out,
            "action": draft.action or IntentAction.ONE.value,
            "event_id": eid,
            "event_name": ename,
            "quantity": draft.quantity,
            "start_time": draft.start_time or 0,
            "end_time": draft.end_time or 0,
            "ignore_time_range": bool(draft.ignore_time_range),
            "remark": (draft.remark or "").strip(),
            "segment_text": draft.text,
            "missing_quantity": bool(draft.missing_quantity),
        }
    ]


def _soft_model_config(draft: SegmentDraft, phrase: str) -> Dict[str, Any]:
    """软确认 pending 的 model_config：预测维 + 飞轮核词标记。"""
    mc: Dict[str, Any] = {
        "_event_soft_confirm": True,
        "_event_soft_phrase": (phrase or "").strip(),
    }
    if _is_predict_draft(draft):
        mc["_type_target"] = TargetType.PREDICT.value
        mc["_type_predict_channel"] = draft.predict_channel or ""
        mc["_type_time_answer"] = draft.time_answer or ""
        mc["_type_read_source"] = "predict"
    else:
        mc["_type_target"] = draft.target_type or ""
        if draft.history_mode:
            mc["_type_history_mode"] = draft.history_mode
        if draft.read_source:
            mc["_type_read_source"] = draft.read_source
    if draft.type_keywords:
        mc["_type_keywords"] = list(draft.type_keywords)
    return mc


def _response_from_soft_candidate(
    draft: SegmentDraft,
    *,
    text: str,
    device_no: str,
    llm_model: Dict[str, Any],
    conversation_id: str,
) -> Dict[str, Any]:
    """
    EVENT 软候选 → 单叶 leaf_confirm 或多叶消歧 pending。

    未确认不执行、不写飞轮；确认后由 intent_pipeline 写短说法。
    """
    leaves = list(draft.disambiguation_leaves or [])
    phrase = (
        (draft.disambiguation_keyword or "").strip()
        or soft_event_phrase_from_segment(draft.text)
        or remark_keyword_fallback(draft.text)
    )
    mc = {**(llm_model or {}), **_soft_model_config(draft, phrase)}

    if len(leaves) >= 2:
        # 多候选：复用父消歧 pending；话术勿套「备注反查」模板
        if _is_predict_draft(draft):
            op_for_pending = ""
        elif draft.target_type == TargetType.READ.value:
            op_for_pending = IntentOp.READ.value
        else:
            op_for_pending = str(draft.op or IntentOp.CREATE.value)
        show = phrase or "该说法"
        lines = [f"「{show}」可能对应多个事件，请选择（回复序号或名称）："]
        for i, leaf in enumerate(leaves, start=1):
            lines.append(f"{i}. {leaf.get('event_name') or ''}")
        pending = create_parent_disambiguation_pending(
            parent={"event_id": "", "event_name": show},
            children=leaves,
            original_utterance=text,
            action=draft.action or IntentAction.ONE.value,
            quantity=draft.quantity,
            match_source=MatchSource.LLM.value,
            device_no=device_no,
            model_config=mc,
            conversation_id=conversation_id or None,
            op=op_for_pending,
            remark="",
            events=_soft_pending_events(draft, leaf=None),
            clarify_message="\n".join(lines),
            history_mode=draft.history_mode or "",
        )
        fields = pending_to_response_fields(pending)
        logger.info(
            "EVENT 软候选多消歧: phrase=%s options=%s",
            phrase,
            len(leaves),
        )
        return {
            "intent_result": IntentResult.model_validate(fields),
            "need_confirm": True,
            "confirm_type": fields.get("confirm_type") or "",
            "confirm_message": fields.get("confirm_message") or "",
            "conversation_id": pending.conversation_id,
            "remark": phrase,
            "intent_cache_hit": False,
            "match_source": MatchSource.LLM.value,
        }

    leaf = leaves[0] if leaves else {}
    ename = str(leaf.get("event_name") or "").strip()
    confirm_message = _soft_confirm_message(draft, ename)
    events = _soft_pending_events(draft, leaf=leaf)
    op_for_pending = str(events[0].get("op") or "") if events else ""
    pending = create_leaf_confirm_pending(
        leaf={
            "event_id": str(leaf.get("event_id") or ""),
            "event_name": ename,
            "extra_names": [],
        },
        original_utterance=text,
        action=draft.action or IntentAction.ONE.value,
        quantity=draft.quantity,
        match_source=MatchSource.LLM.value,
        device_no=device_no,
        model_config=mc,
        conversation_id=conversation_id,
        events=events,
        op=op_for_pending,
        remark=(draft.remark or "").strip(),
        confirm_message=confirm_message,
        start_time=draft.start_time or None,
        end_time=draft.end_time or None,
        event_ids=[str(leaf.get("event_id") or "")]
        if leaf.get("event_id")
        else [],
        history_mode=draft.history_mode or "",
    )
    fields = pending_to_response_fields(pending)
    logger.info(
        "EVENT 软候选单确认: phrase=%s event=%s msg=%s",
        phrase,
        ename,
        confirm_message[:60],
    )
    return {
        "intent_result": IntentResult.model_validate(fields),
        "need_confirm": True,
        "confirm_type": fields.get("confirm_type") or "",
        "confirm_message": fields.get("confirm_message") or "",
        "conversation_id": pending.conversation_id,
        "remark": phrase,
        "intent_cache_hit": False,
        "match_source": MatchSource.LLM.value,
    }


def remark_keyword_fallback(segment: str) -> str:
    """软候选 phrase 兜底：段文前 12 字。"""
    return ((segment or "").strip()[:12]) or ""


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
            "target_type": TargetType.OTHER.value,
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
                "target_type": TargetType.OTHER.value,
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
        logger.info("单事件多维（维级/明细小 LLM 可按需）: %s", text[:60])
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
        # EVENT 软候选：单确认 / 多消歧（未确认不执行）
        if (
            draft.fail_reason == "event_soft_candidate"
            and draft.disambiguation_leaves
        ):
            return _response_from_soft_candidate(
                draft,
                text=text,
                device_no=device_no,
                llm_model=llm_model or {},
                conversation_id=conversation_id or "",
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
        TargetType.OTHER.value,
        TargetType.EXIT.value,
    ):
        need_confirm = False
    # 缺量 / TYPE 需确认：强制门控，避免图直执行
    elif intent.get("missing_quantity") or any(
        isinstance(e, dict) and e.get("missing_quantity")
        for e in (intent.get("events") or [])
    ):
        need_confirm = True
        intent["need_confirm"] = True
    elif intent.get("need_confirm") and (intent.get("confirm_message") or "").strip():
        # TYPE LLM need_confirm=true 已带确认话术
        need_confirm = True

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

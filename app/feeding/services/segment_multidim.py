"""
段级多维拼装

业务说明：
顺序 TYPE → EVENT → REMARK(明细) → SHAPE → QTY → TIME。
事件维阶梯：词典名 → extra_names 精确 → 短说法向量 0.72 → Go 备注反查。
禁止常识升格；miss 记缺口。仅事件飞轮；其它维 miss 写 rule_gap_store。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.feeding.services.closed_interval import apply_time_slots_to_events
from app.feeding.services.event_hierarchy import is_parent_event
from app.feeding.services.event_name_match import (
    match_extra_names,
    match_feeding_event,
)
from app.feeding.services.history_mode_cues import infer_expected_history_mode
from app.feeding.services.intent_cache_store import (
    EVENT_PHRASE_THRESHOLD,
    intent_cache_store,
)
from app.feeding.services.rule_gap_store import rule_gap_store
from app.feeding.services.segment_remark import (
    extract_detail_remark_llm,
    merge_remarks,
    remark_keyword_from_segment,
    resolve_remark_leaves_cached,
)
from app.feeding.utils.quantity_extractor import extract_quantity_from_text
from app.feeding.utils.time_slot_extractor import (
    extract_clocks_from_text,
    has_unconsumed_temporal_residual,
)
from app.shared.constants import IntentAction, IntentOp, MatchSource, TargetType

logger = logging.getLogger(__name__)

_DELETE_RE = re.compile(r"删除|删掉|去掉|取消记录")
_UPDATE_RE = re.compile(r"改成|修改|更正|改一下")
_END_RE = re.compile(r"结束|停了|停掉|喂完了|吃完了")
_EXIT_RE = re.compile(r"^退出$|^拜拜$|^结束对话$")
_SUGGEST_RE = re.compile(r"够不够|正常吗|怎么办|最近怎么样")
_TEMPORAL_HINT = re.compile(
    r"昨天|昨日|前天|今天|今日|昨晚|刚才|刚才|半小时|分钟前|点|时"
)

# 短拼问最大段数（确认策略 C）
MULTI_CONFIRM_BATCH_MAX = 3


@dataclass
class SegmentDraft:
    """单段多维草稿。"""

    text: str
    ok: bool = True
    fail_reason: str = ""
    target_type: str = TargetType.FEEDING.value
    op: str = IntentOp.CREATE.value
    history_mode: str = ""
    event_id: str = ""
    event_name: str = ""
    event_kind: str = "leaf"  # leaf|parent
    event_type: str = ""  # one|time|number
    action: str = IntentAction.ONE.value
    quantity: Optional[int] = None
    missing_quantity: bool = False
    start_time: int = 0
    end_time: int = 0
    ignore_time_range: bool = False
    match_source: str = MatchSource.NAME.value
    match_confidence: float = 0.0
    remark: str = ""
    # 多命中消歧：叶子列表 + 关键字（extra_names 或 Go 反查）
    disambiguation_leaves: List[Dict[str, Any]] = field(default_factory=list)
    disambiguation_keyword: str = ""
    gaps: List[str] = field(default_factory=list)


def resolve_type(
    segment: str,
    *,
    utterance: str,
    sentence_target_type: str = "",
    device_no: str = "",
) -> Tuple[str, str, str]:
    """
    类型维：返回 (target_type, op, history_mode)。

    句级 target_type 优先（查史复合句关键）。
    """
    st = (sentence_target_type or "").strip().lower()
    text = segment or utterance or ""
    if st == TargetType.HISTORY.value or (
        not st and infer_expected_history_mode(text)
    ):
        mode = infer_expected_history_mode(text) or "point"
        # 句级 history 时段内无次数词也保持 daily/point 启发式
        if st == TargetType.HISTORY.value and not infer_expected_history_mode(text):
            mode = infer_expected_history_mode(utterance) or "daily"
        return TargetType.HISTORY.value, IntentOp.READ.value, mode
    if st == TargetType.EXIT.value or _EXIT_RE.search((text or "").strip()):
        return TargetType.EXIT.value, "", ""
    if st == TargetType.CONVERSATION.value or _SUGGEST_RE.search(text):
        return TargetType.CONVERSATION.value, "", ""
    if _DELETE_RE.search(text):
        return TargetType.FEEDING.value, IntentOp.DELETE.value, ""
    if _UPDATE_RE.search(text):
        return TargetType.FEEDING.value, IntentOp.UPDATE.value, ""
    if _END_RE.search(text):
        return TargetType.FEEDING.value, "end", ""
    # 无线索：默认 create；记缺口供扩规则
    if not st and not any(
        k in text for k in ("记录", "吃", "喝", "睡", "尿", "便", "尿布", "奶", "洗")
    ):
        rule_gap_store.record(
            dimension="type",
            segment_text=segment,
            utterance=utterance,
            reason="type_ambiguous",
            device_no=device_no,
        )
    return TargetType.FEEDING.value, IntentOp.CREATE.value, ""


async def resolve_event(
    segment: str,
    *,
    full_events: List[Dict[str, Any]],
    utterance: str,
    device_no: str = "",
    remark_cache: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> Tuple[
    Optional[Dict[str, Any]],
    str,
    float,
    str,
    str,
    List[Dict[str, Any]],
    str,
]:
    """
    事件维阶梯：词典名 → extra_names → 向量 0.72 → Go 备注反查。

    Returns:
        (event, match_source, score, fail_reason, remark,
         disambiguation_leaves, disambiguation_keyword)
    """
    cache = remark_cache if remark_cache is not None else {}

    # 1) 正式名词典匹配（含包含 / 进行态）
    hit = match_feeding_event(segment, full_events)
    if hit:
        return hit, MatchSource.NAME.value, 1.0, "", "", [], ""

    # 2) extra_names 精确（类别/实例别名）→ remark=别名；禁止常识升格
    alias_ev, alias_hits, alias_word = match_extra_names(segment, full_events)
    if len(alias_hits) > 1:
        return (
            None,
            MatchSource.NAME.value,
            0.0,
            "extra_names_ambiguous",
            alias_word,
            alias_hits,
            alias_word,
        )
    if alias_ev is not None:
        return (
            alias_ev,
            MatchSource.NAME.value,
            1.0,
            "",
            alias_word,
            [],
            "",
        )

    # 3) 短说法向量
    phrases = intent_cache_store.search_event_phrase(segment, n_results=1)
    if phrases:
        top = phrases[0]
        score = float(top.get("score") or 0)
        payload = top.get("payload") or {}
        eid = str(payload.get("event_id") or "").strip()
        if score >= EVENT_PHRASE_THRESHOLD and eid:
            ev = None
            for e in full_events:
                if str(e.get("event_id") or "") == eid:
                    ev = e
                    break
            if ev is None:
                ev = {
                    "event_id": eid,
                    "event_name": str(payload.get("event_name") or ""),
                    "type": "one",
                }
            return ev, MatchSource.VECTOR.value, score, "", "", [], ""
        # 低于门槛：不记缺口，继续 Go 反查

    # 4) Go 备注模糊反查（禁止把未命中专名常识升格）
    keyword = remark_keyword_from_segment(segment)
    leaves = await resolve_remark_leaves_cached(
        keyword,
        device_no=device_no,
        full_events=full_events,
        cache=cache,
    )
    if len(leaves) == 1:
        return (
            leaves[0],
            MatchSource.NAME.value,
            1.0,
            "",
            keyword,
            [],
            "",
        )
    if len(leaves) > 1:
        return (
            None,
            MatchSource.NAME.value,
            0.0,
            "remark_ambiguous",
            keyword,
            leaves,
            keyword,
        )

    # 终局 miss：记缺口
    rule_gap_store.record(
        dimension="event",
        segment_text=segment,
        utterance=utterance,
        reason="event_no_hit_after_remark",
        rule_result=f"keyword={keyword}",
        device_no=device_no,
    )
    return None, MatchSource.NAME.value, 0.0, "event_unresolved", "", [], ""


def resolve_shape(
    op: str, event: Dict[str, Any]
) -> Tuple[str, str]:
    """形态维：由事件 type + op 推 action；返回 (action, event_type)。"""
    et = str(event.get("type") or event.get("event_type") or "one").lower()
    if op == "end":
        return IntentAction.END.value, et
    if et == "time" and op == IntentOp.CREATE.value:
        # 无时长时偏 start；有时长由 TIME 维再改 one
        return IntentAction.START.value, et
    return IntentAction.ONE.value, et


async def resolve_segment(
    segment: str,
    *,
    utterance: str,
    full_events: List[Dict[str, Any]],
    sentence_target_type: str = "",
    device_no: str = "",
    remark_cache: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    llm_model: Optional[Dict[str, Any]] = None,
    extract_detail_remark: bool = True,
) -> SegmentDraft:
    """对单段跑完整多维（含 EVENT Go 反查与明细备注 LLM）。"""
    draft = SegmentDraft(text=(segment or "").strip())
    if not draft.text:
        draft.ok = False
        draft.fail_reason = "empty_segment"
        return draft

    tt, op, hm = resolve_type(
        draft.text,
        utterance=utterance,
        sentence_target_type=sentence_target_type,
        device_no=device_no,
    )
    draft.target_type = tt
    draft.op = op
    draft.history_mode = hm

    if tt in (TargetType.CONVERSATION.value, TargetType.EXIT.value):
        return draft

    (
        ev,
        src,
        score,
        fail,
        remark,
        disamb_leaves,
        disamb_kw,
    ) = await resolve_event(
        draft.text,
        full_events=full_events,
        utterance=utterance,
        device_no=device_no,
        remark_cache=remark_cache,
    )
    if disamb_leaves:
        draft.ok = False
        draft.fail_reason = fail or "event_ambiguous"
        draft.remark = remark
        draft.disambiguation_leaves = disamb_leaves
        draft.disambiguation_keyword = disamb_kw
        return draft
    if not ev:
        draft.ok = False
        draft.fail_reason = fail or "event_unresolved"
        return draft

    draft.event_id = str(ev.get("event_id") or "")
    draft.event_name = str(ev.get("event_name") or "")
    draft.event_kind = (
        "parent" if is_parent_event(draft.event_id, full_events) else "leaf"
    )
    draft.match_source = src
    draft.match_confidence = score
    draft.remark = remark or ""

    # 明细备注 LLM（可空）；与别名/反查 remark 合并
    if extract_detail_remark and draft.event_id:
        try:
            llm_r = await extract_detail_remark_llm(
                draft.text,
                draft.event_name,
                llm_model or {},
            )
            draft.remark = merge_remarks(draft.remark, llm_r)
        except Exception as exc:
            logger.warning("明细备注 LLM 失败: %s", exc)

    action, et = resolve_shape(op, ev)
    draft.action = action
    draft.event_type = et

    # QTY
    qty = extract_quantity_from_text(draft.text)
    if qty is None and utterance and draft.text in utterance:
        qty = extract_quantity_from_text(utterance)
    draft.quantity = qty
    if (
        op == IntentOp.CREATE.value
        and et == "number"
        and draft.event_kind == "leaf"
        and qty is None
    ):
        draft.missing_quantity = True
        rule_gap_store.record(
            dimension="quantity",
            segment_text=draft.text,
            utterance=utterance,
            reason="number_leaf_missing_qty",
            device_no=device_no,
        )

    # TIME
    if op == IntentOp.READ.value:
        if hm == "point":
            draft.ignore_time_range = True
        clocks = extract_clocks_from_text(draft.text)
        if clocks and has_unconsumed_temporal_residual(draft.text, clocks):
            rule_gap_store.record(
                dimension="time",
                segment_text=draft.text,
                utterance=utterance,
                reason="time_partial",
                device_no=device_no,
            )
        elif _TEMPORAL_HINT.search(draft.text) and not clocks and hm != "point":
            rule_gap_store.record(
                dimension="time",
                segment_text=draft.text,
                utterance=utterance,
                reason="time_hint_no_clock",
                device_no=device_no,
            )
    else:
        ev_body = {
            "op": op,
            "action": draft.action,
            "event_id": draft.event_id,
            "event_name": draft.event_name,
            "quantity": draft.quantity,
            "start_time": 0,
            "end_time": 0,
        }
        clocks = extract_clocks_from_text(draft.text)
        if clocks and has_unconsumed_temporal_residual(draft.text, clocks):
            rule_gap_store.record(
                dimension="time",
                segment_text=draft.text,
                utterance=utterance,
                reason="time_partial",
                device_no=device_no,
            )
        else:
            new_evs, changed = apply_time_slots_to_events(draft.text, [ev_body])
            if changed and new_evs:
                draft.start_time = int(new_evs[0].get("start_time") or 0)
                draft.end_time = int(new_evs[0].get("end_time") or 0)
                if new_evs[0].get("quantity") is not None:
                    draft.quantity = new_evs[0].get("quantity")
                # 计时补记
                if draft.event_type == "time" and draft.end_time > draft.start_time > 0:
                    draft.action = IntentAction.ONE.value
            elif _TEMPORAL_HINT.search(draft.text) and not clocks:
                rule_gap_store.record(
                    dimension="time",
                    segment_text=draft.text,
                    utterance=utterance,
                    reason="time_hint_no_clock",
                    device_no=device_no,
                )

    return draft


def drafts_to_intent(
    drafts: List[SegmentDraft],
    *,
    utterance: str,
) -> Dict[str, Any]:
    """多段草稿 → intent_result 字典。"""
    if not drafts:
        return {
            "target_type": TargetType.CONVERSATION.value,
            "events": [],
            "content": "没听清，请再说一遍，或把几件事分开说。",
            "need_confirm": False,
            "match_source": MatchSource.NAME.value,
        }

    # conversation / exit 整句
    if len(drafts) == 1 and drafts[0].target_type == TargetType.EXIT.value:
        return {
            "target_type": TargetType.EXIT.value,
            "events": [],
            "content": "",
            "need_confirm": False,
        }
    if len(drafts) == 1 and drafts[0].target_type == TargetType.CONVERSATION.value:
        return {
            "target_type": TargetType.CONVERSATION.value,
            "events": [],
            "content": "暂未开通建议功能",
            "need_confirm": False,
        }

    bad = [d for d in drafts if not d.ok]
    if bad:
        # 反查零命中：文案点名无法识别
        fail_names = []
        for d in bad:
            if d.fail_reason == "event_unresolved":
                kw = remark_keyword_from_segment(d.text)
                if kw:
                    fail_names.append(kw)
        if fail_names:
            unique = list(dict.fromkeys(fail_names))
            shown = "、".join(unique)
            return {
                "target_type": TargetType.CONVERSATION.value,
                "events": [],
                "content": f"无法识别对应的事件「{shown}」。",
                "need_confirm": False,
                "match_source": MatchSource.NAME.value,
                "segment_failed": True,
                "missing_events": unique,
            }
        return {
            "target_type": TargetType.CONVERSATION.value,
            "events": [],
            "content": "没听清有哪几件事，请分开说一下（例如：换尿布了。吃了120奶。）",
            "need_confirm": False,
            "match_source": MatchSource.NAME.value,
            "segment_failed": True,
        }

    events: List[Dict[str, Any]] = []
    history_mode = ""
    target = TargetType.FEEDING.value
    top_remark = ""
    for d in drafts:
        if d.target_type == TargetType.HISTORY.value:
            target = TargetType.HISTORY.value
            history_mode = d.history_mode or history_mode or "point"
        rem = (d.remark or "").strip()
        if rem and not top_remark:
            top_remark = rem
        ev = {
            "op": d.op if d.op != "end" else "end",
            "action": d.action,
            "event_id": d.event_id,
            "event_name": d.event_name,
            "quantity": d.quantity,
            "start_time": d.start_time or 0,
            "end_time": d.end_time or 0,
            "ignore_time_range": bool(d.ignore_time_range),
            "remark": rem,
            "missing_quantity": d.missing_quantity,
            "segment_text": d.text,
        }
        events.append(ev)

    # 缺量：优先阻塞，由管线追问
    missing_qty = any(e.get("missing_quantity") for e in events)
    eids = [str(e.get("event_id") or "") for e in events if e.get("event_id")]
    return {
        "target_type": target,
        "history_mode": history_mode or None,
        "events": events,
        "event_ids": eids,
        "quantity": events[0].get("quantity") if len(events) == 1 else None,
        "event_id": events[0].get("event_id") if len(events) == 1 else "",
        "event_name": events[0].get("event_name") if len(events) == 1 else "",
        "remark": top_remark,
        "match_source": drafts[0].match_source,
        "match_confidence": drafts[0].match_confidence,
        "need_confirm": True,
        "missing_quantity": missing_qty,
        "content": "",
        "confirm_message": "",
        "keywords": [],
        "utterance": utterance,
    }


def should_batch_confirm(events: List[Dict[str, Any]]) -> bool:
    """确认策略 C：短且同质 → 拼问。"""
    if not events or len(events) > MULTI_CONFIRM_BATCH_MAX:
        return False
    ops = {str(e.get("op") or "") for e in events}
    if len(ops) != 1:
        return False
    return True

"""
段级多维拼装

业务说明：
顺序 OP(轨) → EVENT → REMARK(明细) → QTY → TIME（SHAPE 并入 OP）。
OP：整段飞轮 → 小 LLM；短关键词 TYPE 飞轮已停用热路径。
事件维阶梯：词典名 → extra_names → 向量 0.72 → Go 备注反查 → 事件小 LLM。
TIME：规则优先，miss→LLM→rule_gap（无时间飞轮）。
QTY：规则可先，miss→LLM→数量飞轮。
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
from app.feeding.services.dim_resolve import (
    resolve_predict_dims,
    resolve_read_source,
)
from app.feeding.services.op_cue_store import op_cue_store
from app.feeding.services.predict_cue_store import predict_cue_store
from app.feeding.services.qty_cue_store import qty_cue_store
from app.feeding.services.read_source_cue_store import read_source_cue_store
from app.feeding.services.rule_gap_store import rule_gap_store
from app.feeding.services.segment_dim_llm import (
    has_quantity_clue,
    llm_resolve_event,
    llm_resolve_quantity,
    llm_resolve_time,
    llm_resolve_type,
)
from app.feeding.services.segment_outcome import (
    OTHER_UNSUPPORTED_MSG,
    SegmentOutcome,
    summarize_segment_outcomes,
)
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
from app.shared.constants import (
    IntentAction,
    IntentOp,
    MatchSource,
    TargetType,
    normalize_target_rail,
)

logger = logging.getLogger(__name__)

_DELETE_RE = re.compile(r"删除|删掉|去掉|取消记录")
_UPDATE_RE = re.compile(r"改成|修改|更正|改一下")
_EXIT_RE = re.compile(r"^退出$|^拜拜$|^结束对话$")
_OTHER_HINT_RE = re.compile(r"够不够|正常吗|怎么办|最近怎么样")
_END_HINT_RE = re.compile(r"睡醒|醒了|结束|停了|好了")
_TEMPORAL_HINT = re.compile(
    r"昨天|昨日|前天|今天|今日|昨晚|刚才|刚才|半小时|分钟前|点|时"
)
# 短拼问最大段数（确认策略 C，遗留）
MULTI_CONFIRM_BATCH_MAX = 3


@dataclass
class SegmentDraft:
    """单段多维草稿（顶层轨为 C/R/U/D/exit/other）。"""

    text: str
    ok: bool = True
    fail_reason: str = ""
    target_type: str = TargetType.CREATE.value
    op: str = IntentOp.CREATE.value
    # read 子维：record|predict；非 read 须空
    read_source: str = ""
    history_mode: str = ""
    # 预测问答分维（仅 read+predict；其它须空）
    predict_channel: str = ""
    time_answer: str = ""
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
    # OP LLM：是否需确认轨、遗留关键字（飞轮以整段为准）
    type_need_confirm: bool = False
    type_keywords: List[str] = field(default_factory=list)
    # 多命中消歧：叶子列表 + 关键字（extra_names 或 Go 反查）
    disambiguation_leaves: List[Dict[str, Any]] = field(default_factory=list)
    disambiguation_keyword: str = ""
    gaps: List[str] = field(default_factory=list)


def _empty_predict_dims() -> Tuple[str, str]:
    """非 predict 时清空两维。"""
    return "", ""


def _is_read_predict(tt: str, rs: str) -> bool:
    """是否为 R·predict。"""
    return tt == TargetType.READ.value and rs == "predict"


def _is_read_record(tt: str, rs: str) -> bool:
    """是否为 R·record。"""
    return tt == TargetType.READ.value and rs == "record"


async def resolve_type(
    segment: str,
    *,
    utterance: str,
    sentence_target_type: str = "",
    device_no: str = "",
    llm_model: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str, str, str, str, bool, List[str], str]:
    """
    OP 轨：强规则 → 整段 OP 飞轮 →（read 时）R·source 飞轮 → OP 小 LLM。

    业务说明：
    短关键词 TYPE 飞轮已停用；document=整段。
    read 由 read_source 区分 record|predict；不以「多久」本地门闩压 predict。

    Returns:
        (target_type, op, history_mode, predict_channel, time_answer,
         need_confirm, keywords, read_source)
    """
    st_raw = (sentence_target_type or "").strip().lower()
    st = normalize_target_rail(st_raw) if st_raw else ""
    # 句级若仍标旧 predict/history，保留子维线索
    st_legacy = st_raw
    text = segment or utterance or ""
    if st == TargetType.EXIT.value or _EXIT_RE.search((text or "").strip()):
        return TargetType.EXIT.value, "", "", "", "", False, [], ""
    if _OTHER_HINT_RE.search(text) and st in ("", TargetType.OTHER.value):
        return TargetType.OTHER.value, "", "", "", "", False, [], ""
    # 显式改删强线索
    if _DELETE_RE.search(text):
        return TargetType.DELETE.value, IntentOp.DELETE.value, "", "", "", False, [], ""
    if _UPDATE_RE.search(text) and not _END_HINT_RE.search(text):
        return TargetType.UPDATE.value, IntentOp.UPDATE.value, "", "", "", False, [], ""
    if _END_HINT_RE.search(text) and st in ("", TargetType.UPDATE.value, TargetType.CREATE.value):
        # 「睡醒了」类结束计时：U·end（无进行中时由落库层转 C）
        if re.search(r"睡醒|醒了", text):
            return TargetType.UPDATE.value, "end", "", "", "", False, [], ""

    # OP 整段飞轮（仅轨；read 子维走 resolve_read_source / predict）
    skip_history_clue = False
    hit_rail = op_cue_store.search_op_rail(text)
    if hit_rail:
        tt = hit_rail
        if tt == TargetType.READ.value:
            rs_hit, _from_fw = await resolve_read_source(text, llm_model=llm_model)
            if rs_hit == "predict":
                pc, ta, need_p = await resolve_predict_dims(
                    text, llm_model=llm_model or {}
                )
                return (
                    TargetType.READ.value,
                    "",
                    "",
                    pc,
                    ta,
                    need_p,
                    [],
                    "predict",
                )
            if rs_hit == "record":
                hm = infer_expected_history_mode(text) or "point"
                return (
                    TargetType.READ.value,
                    IntentOp.READ.value,
                    hm,
                    "",
                    "",
                    False,
                    [],
                    "record",
                )
            if st_legacy == TargetType.HISTORY.value or infer_expected_history_mode(
                text
            ):
                hm = infer_expected_history_mode(text) or "point"
                return (
                    TargetType.READ.value,
                    IntentOp.READ.value,
                    hm,
                    "",
                    "",
                    False,
                    [],
                    "record",
                )
            # 否则走 LLM 补 read_source / 预测两维
            skip_history_clue = True
        elif tt == TargetType.CREATE.value:
            return tt, IntentOp.CREATE.value, "", "", "", False, [], ""
        elif tt == TargetType.UPDATE.value:
            op = "end" if _END_HINT_RE.search(text) else IntentOp.UPDATE.value
            return tt, op, "", "", "", False, [], ""
        elif tt == TargetType.DELETE.value:
            return tt, IntentOp.DELETE.value, "", "", "", False, [], ""
        elif tt in (TargetType.EXIT.value, TargetType.OTHER.value):
            return tt, "", "", "", "", False, [], ""

    # 查史强线索（上一次/几次等）→ read+record；不用「多久」压 predict
    if not skip_history_clue and (
        st_legacy == TargetType.HISTORY.value
        or (not st_legacy and infer_expected_history_mode(text))
    ):
        mode = infer_expected_history_mode(text) or "point"
        if st_legacy == TargetType.HISTORY.value and not infer_expected_history_mode(text):
            mode = infer_expected_history_mode(utterance) or "daily"
        return (
            TargetType.READ.value,
            IntentOp.READ.value,
            mode,
            "",
            "",
            False,
            [],
            "record",
        )

    # 冷路径：OP 小 LLM；成功后拆写 OP / source / predict 各层
    try:
        tt, op, hm, pc, ta, need_confirm, keywords, summary, rs = await llm_resolve_type(
            text, llm_model or {}
        )
        logger.info("OP LLM: %s", summary[:200])
        if not need_confirm and tt:
            doc = text.strip()
            op_cue_store.add(doc, tt)
            if tt == TargetType.READ.value and rs in ("record", "predict"):
                read_source_cue_store.add(doc, rs)
            if (
                tt == TargetType.READ.value
                and rs == "predict"
                and pc in ("active", "next")
                and ta in ("clock", "remain")
            ):
                predict_cue_store.add(doc, pc, ta)
            # read+predict 但两维残缺：交独立预测维补齐
            if tt == TargetType.READ.value and rs == "predict" and (
                pc not in ("active", "next") or ta not in ("clock", "remain")
            ):
                pc2, ta2, need_p = await resolve_predict_dims(
                    doc, llm_model=llm_model or {}
                )
                return tt, op, hm, pc2, ta2, need_p or need_confirm, keywords, rs
        return tt, op, hm, pc, ta, need_confirm, keywords, rs
    except Exception as exc:
        logger.warning("OP 小 LLM 失败: %s", exc)
        return TargetType.CREATE.value, IntentOp.CREATE.value, "", "", "", True, [], ""


async def resolve_event(
    segment: str,
    *,
    full_events: List[Dict[str, Any]],
    utterance: str,
    device_no: str = "",
    remark_cache: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    llm_model: Optional[Dict[str, Any]] = None,
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
    事件维阶梯：词典 → extra_names → 向量 → Go 反查 → 事件小 LLM。

    Returns:
        (event, match_source, score, fail_reason, remark,
         disambiguation_leaves, disambiguation_keyword)
    """
    cache = remark_cache if remark_cache is not None else {}

    # 1) 正式名词典匹配
    hit = match_feeding_event(segment, full_events)
    if hit:
        return hit, MatchSource.NAME.value, 1.0, "", "", [], ""

    # 2) extra_names 精确
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

    # 4) Go 备注模糊反查
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

    # 5) 事件小 LLM（表内对齐；专名无把握须空）
    try:
        ev_llm, summary = await llm_resolve_event(
            segment, full_events, llm_model or {}
        )
    except Exception as exc:
        logger.warning("EVENT 小 LLM 失败: %s", exc)
        ev_llm, summary = None, str(exc)[:200]
    if ev_llm is not None:
        # 冷路径成功：整段回写事件飞轮（与 OP/qty 同构）
        eid = str(ev_llm.get("event_id") or "").strip()
        ename = str(ev_llm.get("event_name") or "").strip()
        if eid and (segment or "").strip():
            intent_cache_store.add_event_phrase(
                (segment or "").strip(),
                event_id=eid,
                event_name=ename,
                kind="leaf",
            )
        return (
            ev_llm,
            MatchSource.LLM.value,
            1.0,
            "",
            "",
            [],
            "",
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
        return IntentAction.START.value, et
    return IntentAction.ONE.value, et


async def _apply_time_llm(
    draft: SegmentDraft,
    *,
    utterance: str,
    device_no: str,
    llm_model: Dict[str, Any],
    reason: str,
) -> None:
    """弃权残缺规则时间后调 TIME 小 LLM。"""
    draft.start_time = 0
    draft.end_time = 0
    try:
        st, et, summary = await llm_resolve_time(draft.text, llm_model)
    except Exception as exc:
        logger.warning("TIME 小 LLM 失败: %s", exc)
        rule_gap_store.record(
            dimension="time",
            segment_text=draft.text,
            utterance=utterance,
            reason=f"{reason}_llm_fail",
            llm_used=True,
            llm_result=str(exc)[:200],
            device_no=device_no,
        )
        return
    rule_gap_store.record(
        dimension="time",
        segment_text=draft.text,
        utterance=utterance,
        reason=reason,
        llm_used=True,
        llm_result=summary,
        device_no=device_no,
    )
    if st is not None and st > 0:
        draft.start_time = st
        draft.end_time = int(et or st)
        if draft.event_type == "time" and draft.end_time > draft.start_time:
            draft.action = IntentAction.ONE.value


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
    """
    对单段跑完整多维。

    顺序：OP(飞轮/LLM) → EVENT(…→Go→LLM) → 明细备注 LLM → QTY → TIME。
    """
    model = llm_model or {}
    draft = SegmentDraft(text=(segment or "").strip())
    if not draft.text:
        draft.ok = False
        draft.fail_reason = "empty_segment"
        return draft

    tt, op, hm, pc, ta, type_need_confirm, type_keywords, rs = await resolve_type(
        draft.text,
        utterance=utterance,
        sentence_target_type=sentence_target_type,
        device_no=device_no,
        llm_model=model,
    )
    draft.target_type = tt
    draft.op = op
    draft.history_mode = hm
    draft.read_source = rs if tt == TargetType.READ.value else ""
    if _is_read_predict(tt, draft.read_source):
        draft.predict_channel = pc if pc in ("active", "next") else ""
        draft.time_answer = ta if ta in ("clock", "remain") else ""
        draft.op = ""
        draft.history_mode = ""
    else:
        draft.predict_channel = ""
        draft.time_answer = ""
    draft.type_need_confirm = bool(type_need_confirm)
    draft.type_keywords = list(type_keywords or [])

    if tt in (TargetType.EXIT.value, TargetType.OTHER.value):
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
        llm_model=model,
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

    # 明细备注 LLM（事件已定后）；与别名/反查 remark 合并
    if extract_detail_remark and draft.event_id:
        try:
            llm_r = await extract_detail_remark_llm(
                draft.text,
                draft.event_name,
                model,
            )
            draft.remark = merge_remarks(draft.remark, llm_r)
        except Exception as exc:
            logger.warning("明细备注 LLM 失败: %s", exc)

    # R·predict：事件已定即可，跳过形态/量/时间
    if _is_read_predict(tt, draft.read_source):
        draft.action = ""
        draft.event_type = str(ev.get("type") or ev.get("event_type") or "")
        return draft

    # 形态由 OP.op 推导（不再独立 SHAPE LLM）
    action, et = resolve_shape(op, ev)
    draft.action = action
    draft.event_type = et
    if et == "time" and op == "end":
        draft.action = IntentAction.END.value
    # create + time 无闭合起止 → 追问（U·end 转 C 时同样适用）
    if (
        tt == TargetType.CREATE.value
        and et == "time"
        and draft.event_kind == "leaf"
        and not (draft.start_time > 0 and draft.end_time > draft.start_time)
    ):
        # 时间槽在 TIME 段填充后再二次检查；此处先占位
        pass

    # QTY：飞轮 → 规则 →（有线索）小 LLM → 回写飞轮；number 无线索则追问
    qty = qty_cue_store.search_quantity(draft.text)
    if qty is None:
        qty = extract_quantity_from_text(draft.text)
    if qty is None and utterance and draft.text in utterance:
        qty = extract_quantity_from_text(utterance)
    qty_from_llm = False
    if qty is None and has_quantity_clue(draft.text):
        try:
            qty_llm, summary = await llm_resolve_quantity(draft.text, model)
        except Exception as exc:
            logger.warning("QTY 小 LLM 失败: %s", exc)
            qty_llm, summary = None, str(exc)[:200]
        rule_gap_store.record(
            dimension="quantity",
            segment_text=draft.text,
            utterance=utterance,
            reason="quantity_clue_llm",
            llm_used=True,
            llm_result=summary,
            device_no=device_no,
        )
        qty = qty_llm
        qty_from_llm = qty is not None
    draft.quantity = qty
    if qty_from_llm and qty is not None:
        qty_cue_store.add(draft.text, int(qty))
    if (
        tt in (TargetType.CREATE.value, TargetType.UPDATE.value)
        and op in (IntentOp.CREATE.value, IntentOp.UPDATE.value, "end", "")
        and et == "number"
        and draft.event_kind == "leaf"
        and qty is None
    ):
        # 无量线索：缺量追问；不写数量飞轮
        draft.missing_quantity = True

    # TIME（无飞轮）
    if _is_read_record(tt, draft.read_source) or op == IntentOp.READ.value:
        if hm == "point":
            draft.ignore_time_range = True
        clocks = extract_clocks_from_text(draft.text)
        if clocks and has_unconsumed_temporal_residual(draft.text, clocks):
            await _apply_time_llm(
                draft,
                utterance=utterance,
                device_no=device_no,
                llm_model=model,
                reason="time_partial_llm",
            )
        elif _TEMPORAL_HINT.search(draft.text) and not clocks and hm != "point":
            await _apply_time_llm(
                draft,
                utterance=utterance,
                device_no=device_no,
                llm_model=model,
                reason="time_hint_no_clock_llm",
            )
    else:
        ev_body = {
            "op": op if op != "end" else "end",
            "action": draft.action,
            "event_id": draft.event_id,
            "event_name": draft.event_name,
            "quantity": draft.quantity,
            "start_time": 0,
            "end_time": 0,
        }
        clocks = extract_clocks_from_text(draft.text)
        if clocks and has_unconsumed_temporal_residual(draft.text, clocks):
            await _apply_time_llm(
                draft,
                utterance=utterance,
                device_no=device_no,
                llm_model=model,
                reason="time_partial_llm",
            )
        else:
            new_evs, changed = apply_time_slots_to_events(draft.text, [ev_body])
            if changed and new_evs:
                draft.start_time = int(new_evs[0].get("start_time") or 0)
                draft.end_time = int(new_evs[0].get("end_time") or 0)
                if new_evs[0].get("quantity") is not None:
                    draft.quantity = new_evs[0].get("quantity")
                if draft.event_type == "time" and draft.end_time > draft.start_time > 0:
                    draft.action = IntentAction.ONE.value
            elif _TEMPORAL_HINT.search(draft.text) and not clocks:
                await _apply_time_llm(
                    draft,
                    utterance=utterance,
                    device_no=device_no,
                    llm_model=model,
                    reason="time_hint_no_clock_llm",
                )

    # create + time：仍无闭合起止则缺槽追问
    if (
        tt == TargetType.CREATE.value
        and draft.event_type == "time"
        and draft.event_kind == "leaf"
        and draft.action != IntentAction.START.value
        and not (draft.start_time > 0 and draft.end_time > draft.start_time)
        and op != "end"
    ):
        # 开始计时（仅 start）允许 end=0；补记闭合须双端
        if draft.action != IntentAction.START.value and draft.op == IntentOp.CREATE.value:
            if draft.start_time <= 0 or draft.end_time <= draft.start_time:
                # 仅当语义像补记闭合（已有双钟点线索失败）时追问；开表不追
                if draft.action == IntentAction.ONE.value:
                    draft.ok = False
                    draft.fail_reason = "time_not_closed"
                    draft.gaps.append("time_closed_interval")

    return draft


def drafts_to_intent(
    drafts: List[SegmentDraft],
    *,
    utterance: str,
) -> Dict[str, Any]:
    """多段草稿 → intent_result 字典（顶层六轨）。"""
    if not drafts:
        return {
            "target_type": TargetType.OTHER.value,
            "events": [],
            "content": "没听清，请再说一遍，或把几件事分开说。",
            "need_confirm": False,
            "match_source": MatchSource.NAME.value,
        }

    if len(drafts) == 1 and drafts[0].target_type == TargetType.EXIT.value:
        return {
            "target_type": TargetType.EXIT.value,
            "events": [],
            "content": "",
            "need_confirm": False,
        }
    if len(drafts) == 1 and drafts[0].target_type == TargetType.OTHER.value:
        return {
            "target_type": TargetType.OTHER.value,
            "events": [],
            "content": OTHER_UNSUPPORTED_MSG,
            "need_confirm": False,
        }

    # 失败段收集澄清话术；成功段继续组装（不阻断其它段）
    outcomes: List[SegmentOutcome] = []
    ok_drafts: List[SegmentDraft] = []
    for d in drafts:
        if d.target_type == TargetType.OTHER.value:
            outcomes.append(
                SegmentOutcome(
                    segment_text=d.text,
                    rail="other",
                    status="other",
                    message=OTHER_UNSUPPORTED_MSG,
                )
            )
            continue
        if d.target_type == TargetType.EXIT.value:
            outcomes.append(
                SegmentOutcome(
                    segment_text=d.text,
                    rail="exit",
                    status="exit",
                    message="好的，已结束对话",
                )
            )
            continue
        if not d.ok:
            if d.fail_reason == "event_unresolved":
                kw = remark_keyword_from_segment(d.text) or d.text[:20]
                outcomes.append(
                    SegmentOutcome(
                        segment_text=d.text,
                        rail=d.target_type,
                        status="clarify",
                        message=f"无法识别对应的事件「{kw}」",
                        need_clarify=True,
                    )
                )
            elif d.fail_reason == "time_not_closed":
                name = (d.event_name or d.text)[:20]
                outcomes.append(
                    SegmentOutcome(
                        segment_text=d.text,
                        rail=d.target_type,
                        status="clarify",
                        message=f"{name}需要补充开始和结束时间",
                        need_clarify=True,
                    )
                )
            else:
                outcomes.append(
                    SegmentOutcome(
                        segment_text=d.text,
                        rail=d.target_type,
                        status="clarify",
                        message="这段没听清，请再说一遍",
                        need_clarify=True,
                    )
                )
            continue
        ok_drafts.append(d)

    if not ok_drafts:
        summary = summarize_segment_outcomes(outcomes)
        if not summary:
            summary = "没听清有哪几件事，请分开说一下（例如：换尿布了。吃了120奶。）"
        any_clarify = any(o.need_clarify for o in outcomes)
        return {
            "target_type": TargetType.OTHER.value,
            "events": [],
            "content": summary,
            "need_confirm": bool(any_clarify),
            "match_source": MatchSource.NAME.value,
            "segment_failed": True,
            "missing_events": [
                remark_keyword_from_segment(o.segment_text) or o.segment_text[:20]
                for o in outcomes
                if o.status == "clarify" and "无法识别" in (o.message or "")
            ],
        }

    events: List[Dict[str, Any]] = []
    history_mode = ""
    predict_channel = ""
    time_answer = ""
    read_source = ""
    # 多段优先：predict > record > CUD 首轨
    target = TargetType.CREATE.value
    top_remark = ""
    for d in ok_drafts:
        if _is_read_predict(d.target_type, d.read_source):
            target = TargetType.READ.value
            read_source = "predict"
            history_mode = ""
            if d.predict_channel in ("active", "next"):
                predict_channel = d.predict_channel
            if d.time_answer in ("clock", "remain"):
                time_answer = d.time_answer
        elif _is_read_record(d.target_type, d.read_source):
            if read_source != "predict":
                target = TargetType.READ.value
                read_source = "record"
                history_mode = d.history_mode or history_mode or "point"
        elif d.target_type in (
            TargetType.UPDATE.value,
            TargetType.DELETE.value,
            TargetType.CREATE.value,
        ):
            if target != TargetType.READ.value:
                target = d.target_type
        rem = (d.remark or "").strip()
        if rem and not top_remark:
            top_remark = rem
        # predict 子项 op 空，禁止伪装成 read 进查史
        if _is_read_predict(d.target_type, d.read_source):
            op_out = ""
        elif d.op == "end":
            op_out = "end"
        elif d.target_type == TargetType.UPDATE.value and d.op != "end":
            op_out = IntentOp.UPDATE.value
        elif d.target_type == TargetType.DELETE.value:
            op_out = IntentOp.DELETE.value
        elif _is_read_record(d.target_type, d.read_source):
            op_out = IntentOp.READ.value
        else:
            op_out = d.op or IntentOp.CREATE.value
        ev = {
            "op": op_out,
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
        outcomes.append(
            SegmentOutcome(
                segment_text=d.text,
                rail=d.target_type,
                status="ok",
                message="",
            )
        )

    missing_qty = any(e.get("missing_quantity") for e in events)
    # 父事件 CUD 须消歧；R 可带父 id
    parent_cud_block = False
    for d in ok_drafts:
        if (d.event_kind or "") != "parent":
            continue
        if d.target_type == TargetType.READ.value:
            continue
        op = str(d.op or "").strip().lower()
        if op == IntentOp.READ.value:
            continue
        parent_cud_block = True
        break
    type_need = any(bool(d.type_need_confirm) for d in ok_drafts)
    if read_source == "predict" and (
        predict_channel not in ("active", "next")
        or time_answer not in ("clock", "remain")
    ):
        type_need = True
    type_kws: List[str] = []
    for d in ok_drafts:
        for k in d.type_keywords or []:
            s = str(k or "").strip()
            if s and s not in type_kws:
                type_kws.append(s)
    need_confirm = bool(missing_qty or parent_cud_block or type_need)
    confirm_message = ""
    if type_need and not missing_qty:
        head_name = str(events[0].get("event_name") or "") if events else ""
        if read_source == "predict":
            confirm_message = f"您是要问「{head_name or '相关事件'}」大概还要多久吗？"
        elif read_source == "record":
            confirm_message = f"您是要查询「{head_name or '相关记录'}」吗？"
        elif any(str(e.get("op") or "") == "end" for e in events):
            confirm_message = f"您是要结束「{head_name or '计时'}」吗？"
        else:
            confirm_message = f"您是要记录「{head_name or '该事件'}」吗？"
    eids = [str(e.get("event_id") or "") for e in events if e.get("event_id")]
    if read_source != "predict":
        predict_channel = ""
        time_answer = ""
    # 失败/other 段话术预置；成功段 content 由落库/播报节点填充后再拼
    pre_summary = summarize_segment_outcomes(
        [o for o in outcomes if o.status in ("clarify", "other", "error")]
    )
    return {
        "target_type": target,
        "read_source": read_source or None,
        "history_mode": history_mode or None,
        "predict_channel": predict_channel or None,
        "time_answer": time_answer or None,
        "events": events,
        "event_ids": eids,
        "quantity": events[0].get("quantity") if len(events) == 1 else None,
        "event_id": events[0].get("event_id") if len(events) == 1 else "",
        "event_name": events[0].get("event_name") if len(events) == 1 else "",
        "remark": top_remark,
        "match_source": ok_drafts[0].match_source,
        "match_confidence": ok_drafts[0].match_confidence,
        "need_confirm": need_confirm,
        "missing_quantity": missing_qty,
        "content": pre_summary,
        "confirm_message": confirm_message,
        "keywords": type_kws,
        "utterance": utterance,
        "segment_outcome_summary": pre_summary,
    }


def should_batch_confirm(events: List[Dict[str, Any]]) -> bool:
    """
    旧确认策略 C：短且同质是否可拼问。

    业务说明：
    直执行改造后多段不再拼 yes/no；保留函数供兼容调用方探测同质。
    """
    if not events or len(events) > MULTI_CONFIRM_BATCH_MAX:
        return False
    ops = {str(e.get("op") or "") for e in events}
    if len(ops) != 1:
        return False
    return True

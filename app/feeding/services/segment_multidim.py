"""
段级多维拼装

业务说明：
顺序 TYPE → EVENT → REMARK(明细) → QTY → TIME（SHAPE 并入 TYPE）。
TYPE：类型关键字飞轮 → 小 LLM（need_confirm/keywords）；弱喂养词不再短路 create。
事件维阶梯：词典名 → extra_names → 向量 0.72 → Go 备注反查 → 事件小 LLM。
TIME/QTY：规则优先，miss 后 LLM 并写 rule_gap；type/event/shape 不写缺口。
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
from app.feeding.services.segment_dim_llm import (
    has_quantity_clue,
    llm_resolve_event,
    llm_resolve_quantity,
    llm_resolve_time,
    llm_resolve_type,
)
from app.feeding.services.type_cue_store import (
    TYPE_CUE_THRESHOLD,
    type_cue_store,
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
from app.shared.constants import IntentAction, IntentOp, MatchSource, TargetType

logger = logging.getLogger(__name__)

_DELETE_RE = re.compile(r"删除|删掉|去掉|取消记录")
_UPDATE_RE = re.compile(r"改成|修改|更正|改一下")
_EXIT_RE = re.compile(r"^退出$|^拜拜$|^结束对话$")
_SUGGEST_RE = re.compile(r"够不够|正常吗|怎么办|最近怎么样")
_TEMPORAL_HINT = re.compile(
    r"昨天|昨日|前天|今天|今日|昨晚|刚才|刚才|半小时|分钟前|点|时"
)
# 短拼问最大段数（确认策略 C，遗留）
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
    # 预测问答分维（仅 predict；非 predict 须空）
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
    # TYPE LLM：是否需确认类型、待写入关键字
    type_need_confirm: bool = False
    type_keywords: List[str] = field(default_factory=list)
    # 多命中消歧：叶子列表 + 关键字（extra_names 或 Go 反查）
    disambiguation_leaves: List[Dict[str, Any]] = field(default_factory=list)
    disambiguation_keyword: str = ""
    gaps: List[str] = field(default_factory=list)


def _empty_predict_dims() -> Tuple[str, str]:
    """非 predict 时清空两维。"""
    return "", ""


async def resolve_type(
    segment: str,
    *,
    utterance: str,
    sentence_target_type: str = "",
    device_no: str = "",
    llm_model: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str, str, str, str, bool, List[str]]:
    """
    类型维：强规则 → 类型关键字飞轮 → TYPE 小 LLM。

    业务说明：
    predict 由飞轮/TYPE LLM 判定两维；不以本地「多久」词表强制 history。
    飞轮命中合法 predict 时优先于查史 point/daily 强线索（predict 优先门闩）。

    Returns:
        (target_type, op, history_mode, predict_channel, time_answer,
         need_confirm, keywords)
    """
    st = (sentence_target_type or "").strip().lower()
    text = segment or utterance or ""
    if st == TargetType.EXIT.value or _EXIT_RE.search((text or "").strip()):
        return TargetType.EXIT.value, "", "", "", "", False, []
    if st == TargetType.CONVERSATION.value or _SUGGEST_RE.search(text):
        return TargetType.CONVERSATION.value, "", "", "", "", False, []
    # 显式改删强线索
    if _DELETE_RE.search(text):
        return TargetType.FEEDING.value, IntentOp.DELETE.value, "", "", "", False, []
    if _UPDATE_RE.search(text):
        return TargetType.FEEDING.value, IntentOp.UPDATE.value, "", "", "", False, []

    # 类型关键字飞轮（含 predict；合法 predict 优先于下方查史强线索）
    hits = type_cue_store.search_type_cue(text, n_results=1)
    if hits:
        top = hits[0]
        score = float(top.get("score") or 0)
        if score >= TYPE_CUE_THRESHOLD:
            pl = top.get("payload") or {}
            tt = str(pl.get("target_type") or TargetType.FEEDING.value).strip().lower()
            op = str(pl.get("op") or "").strip().lower()
            hm = str(pl.get("history_mode") or "").strip().lower()
            pc = str(pl.get("predict_channel") or "").strip().lower()
            ta = str(pl.get("time_answer") or "").strip().lower()
            if tt == TargetType.PREDICT.value:
                # 两维非法视为未命中，继续冷路径（勿用半残 predict）
                if pc in ("active", "next") and ta in ("clock", "remain"):
                    logger.info(
                        "类型飞轮命中 predict: doc=%s score=%s ch=%s ta=%s",
                        str(top.get("document") or "")[:40],
                        score,
                        pc,
                        ta,
                    )
                    return (
                        TargetType.PREDICT.value,
                        "",
                        "",
                        pc,
                        ta,
                        False,
                        [],
                    )
            else:
                if tt == TargetType.HISTORY.value:
                    op = IntentOp.READ.value
                    if hm not in ("point", "daily"):
                        hm = "point"
                pc, ta = _empty_predict_dims()
                logger.info(
                    "类型飞轮命中: doc=%s score=%s tt=%s op=%s",
                    str(top.get("document") or "")[:40],
                    score,
                    tt,
                    op,
                )
                return tt, op, hm, pc, ta, False, []

    # 句级 / 查史强线索（上一次/几次等）；不用「多久」本地门闩压 predict
    if st == TargetType.HISTORY.value or (
        not st and infer_expected_history_mode(text)
    ):
        mode = infer_expected_history_mode(text) or "point"
        if st == TargetType.HISTORY.value and not infer_expected_history_mode(text):
            mode = infer_expected_history_mode(utterance) or "daily"
        return (
            TargetType.HISTORY.value,
            IntentOp.READ.value,
            mode,
            "",
            "",
            False,
            [],
        )
    if st == TargetType.PREDICT.value:
        # 句级已标 predict 但无飞轮两维：交 TYPE LLM 补齐
        pass

    # 冷路径：TYPE 小 LLM（不再因「睡/吃」短路 create）
    try:
        tt, op, hm, pc, ta, need_confirm, keywords, summary = await llm_resolve_type(
            text, llm_model or {}
        )
        logger.info("TYPE LLM: %s", summary[:200])
        if not need_confirm:
            kws = keywords or ([text.strip()] if text.strip() else [])
            type_cue_store.add_type_keywords(
                kws,
                target_type=tt,
                op=op,
                history_mode=hm,
                predict_channel=pc,
                time_answer=ta,
            )
        return tt, op, hm, pc, ta, need_confirm, keywords
    except Exception as exc:
        logger.warning("TYPE 小 LLM 失败: %s", exc)
        return TargetType.FEEDING.value, IntentOp.CREATE.value, "", "", "", True, []


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
        # 事件种子走短说法库 / Hub，不写 rule_gap
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

    顺序：TYPE(飞轮/LLM) → EVENT(…→Go→LLM) → 明细备注 LLM → QTY → TIME。
    """
    model = llm_model or {}
    draft = SegmentDraft(text=(segment or "").strip())
    if not draft.text:
        draft.ok = False
        draft.fail_reason = "empty_segment"
        return draft

    tt, op, hm, pc, ta, type_need_confirm, type_keywords = await resolve_type(
        draft.text,
        utterance=utterance,
        sentence_target_type=sentence_target_type,
        device_no=device_no,
        llm_model=model,
    )
    draft.target_type = tt
    draft.op = op
    draft.history_mode = hm
    # 非 predict 强制清空两维
    if tt == TargetType.PREDICT.value:
        draft.predict_channel = pc if pc in ("active", "next") else ""
        draft.time_answer = ta if ta in ("clock", "remain") else ""
        draft.op = ""
        draft.history_mode = ""
    else:
        draft.predict_channel = ""
        draft.time_answer = ""
    draft.type_need_confirm = bool(type_need_confirm)
    draft.type_keywords = list(type_keywords or [])

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

    # 预测问答：事件已定即可，跳过形态/量/时间（不进查史用时）
    if tt == TargetType.PREDICT.value:
        draft.action = ""
        draft.event_type = str(ev.get("type") or ev.get("event_type") or "")
        return draft

    # 形态由 TYPE.op 推导（不再独立 SHAPE LLM）
    action, et = resolve_shape(op, ev)
    draft.action = action
    draft.event_type = et
    if et == "time" and op == "end":
        draft.action = IntentAction.END.value

    # QTY：规则 →（有线索抽空）小 LLM → number 无线索则追问
    qty = extract_quantity_from_text(draft.text)
    if qty is None and utterance and draft.text in utterance:
        qty = extract_quantity_from_text(utterance)
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
    draft.quantity = qty
    if (
        op == IntentOp.CREATE.value
        and et == "number"
        and draft.event_kind == "leaf"
        and qty is None
    ):
        # 无量线索：缺量追问；不写缺口箱（Hub 只要规则+LLM 类）
        draft.missing_quantity = True

    # TIME
    if op == IntentOp.READ.value:
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
            # 半命中：禁止用残缺规则时间，走 TIME LLM
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
    predict_channel = ""
    time_answer = ""
    target = TargetType.FEEDING.value
    top_remark = ""
    for d in drafts:
        if d.target_type == TargetType.PREDICT.value:
            # predict 优先于 history；多段时以 predict 为准
            target = TargetType.PREDICT.value
            history_mode = ""
            if d.predict_channel in ("active", "next"):
                predict_channel = d.predict_channel
            if d.time_answer in ("clock", "remain"):
                time_answer = d.time_answer
        elif d.target_type == TargetType.HISTORY.value and target != TargetType.PREDICT.value:
            target = TargetType.HISTORY.value
            history_mode = d.history_mode or history_mode or "point"
        rem = (d.remark or "").strip()
        if rem and not top_remark:
            top_remark = rem
        # predict 子项 op 空，禁止伪装成 read 进查史
        op_out = "" if d.target_type == TargetType.PREDICT.value else (
            d.op if d.op != "end" else "end"
        )
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

    missing_qty = any(e.get("missing_quantity") for e in events)
    # 父事件 CUD（create/update/delete/end）须消歧，不得直执行；查史/预测可带父 id
    parent_cud_block = False
    for d in drafts:
        if (d.event_kind or "") != "parent":
            continue
        if d.target_type in (
            TargetType.HISTORY.value,
            TargetType.PREDICT.value,
        ):
            continue
        op = str(d.op or "").strip().lower()
        if op == IntentOp.READ.value:
            continue
        parent_cud_block = True
        break
    # 无阻塞（缺量/父 CUD/TYPE 需确认）时直执行
    type_need = any(bool(d.type_need_confirm) for d in drafts)
    # predict 缺两维也须确认，避免半残路由
    if target == TargetType.PREDICT.value and (
        predict_channel not in ("active", "next")
        or time_answer not in ("clock", "remain")
    ):
        type_need = True
    type_kws: List[str] = []
    for d in drafts:
        for k in d.type_keywords or []:
            s = str(k or "").strip()
            if s and s not in type_kws:
                type_kws.append(s)
    need_confirm = bool(missing_qty or parent_cud_block or type_need)
    confirm_message = ""
    if type_need and not missing_qty:
        # TYPE LLM 自报需确认：简短类型问句
        head_name = str(events[0].get("event_name") or "") if events else ""
        if target == TargetType.PREDICT.value:
            confirm_message = f"您是要问「{head_name or '相关事件'}」大概还要多久吗？"
        elif target == TargetType.HISTORY.value:
            confirm_message = f"您是要查询「{head_name or '相关记录'}」吗？"
        elif any(str(e.get("op") or "") == "end" for e in events):
            confirm_message = f"您是要结束「{head_name or '计时'}」吗？"
        else:
            confirm_message = f"您是要记录「{head_name or '该事件'}」吗？"
    eids = [str(e.get("event_id") or "") for e in events if e.get("event_id")]
    if target != TargetType.PREDICT.value:
        predict_channel = ""
        time_answer = ""
    return {
        "target_type": target,
        "history_mode": history_mode or None,
        "predict_channel": predict_channel or None,
        "time_answer": time_answer or None,
        "events": events,
        "event_ids": eids,
        "quantity": events[0].get("quantity") if len(events) == 1 else None,
        "event_id": events[0].get("event_id") if len(events) == 1 else "",
        "event_name": events[0].get("event_name") if len(events) == 1 else "",
        "remark": top_remark,
        "match_source": drafts[0].match_source,
        "match_confidence": drafts[0].match_confidence,
        "need_confirm": need_confirm,
        "missing_quantity": missing_qty,
        "content": "",
        "confirm_message": confirm_message,
        "keywords": type_kws,
        "utterance": utterance,
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

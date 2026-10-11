"""
段维多维小 LLM 兜底

业务说明：
TYPE / EVENT / TIME / QTY / SHAPE 规则 miss 后的窄契约调用；
经 stream_llm_collect 透出 reasoning。禁止满血多 events 输出。
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from app.feeding.graphs.nodes.prompts.system import (
    SEGMENT_EVENT_LLM_PROMPT,
    SEGMENT_QTY_LLM_PROMPT,
    SEGMENT_SHAPE_LLM_PROMPT,
    SEGMENT_TIME_LLM_PROMPT,
    SEGMENT_TYPE_LLM_PROMPT,
)
from app.feeding.services.event_hierarchy import get_leaf_events
from app.shared.graphs.stream_llm_collect import stream_llm_collect
from app.shared.llm_client import llm_model_config_from_mapping

logger = logging.getLogger(__name__)

_JSON_BLOCK = re.compile(r"\{[\s\S]*\}")
# 事件表注入上限，避免 prompt 过长
_MAX_EVENT_LINES = 120


def _shanghai_tz() -> ZoneInfo:
    """延迟加载时区，避免无 tzdata 的环境在 import 期崩掉。"""
    return ZoneInfo("Asia/Shanghai")

# 数量线索（有线索才调 QTY LLM；无则 number 叶走追问）
_QTY_CLUE_RE = re.compile(
    r"(?:\d+\s*(?:毫升|ml|ML|ｍｌ))"
    r"|(?:吃了|喝了|喂了)\s*\d+"
    r"|(?:[一二两三四五六七八九十百]+)\s*(?:毫升|ml)?"
    r"|(?:\d+\s*(?:配方|母乳|奶粉|辅食|水))"
)

# 计时结束口语（TYPE/SHAPE 共用；须在「睡」喂养线索之前匹配）
END_CUE_RE = re.compile(
    r"结束|停了|停掉|喂完了|吃完了|睡完|睡醒|醒了|醒啦|醒过来|起床了|起床"
)
# 计时开始口语（与结束同时出现则形态暧昧 → SHAPE LLM）
START_CUE_RE = re.compile(r"睡着|入睡|开始睡|哄睡|睡觉了")


def _parse_json_obj(content: str) -> Dict[str, Any]:
    """从 LLM 正文解析 JSON 对象。"""
    raw = (content or "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = _JSON_BLOCK.search(raw)
        if not m:
            return {}
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return {}
    return data if isinstance(data, dict) else {}


def has_quantity_clue(text: str) -> bool:
    """段内是否存在数量口语线索（规则未必能抽出）。"""
    return bool(_QTY_CLUE_RE.search(text or ""))


def matches_end_cue(text: str) -> bool:
    """是否命中计时/记录结束口语线索。"""
    return bool(END_CUE_RE.search(text or ""))


def matches_start_cue(text: str) -> bool:
    """是否命中计时开始口语线索。"""
    return bool(START_CUE_RE.search(text or ""))


def needs_shape_llm(text: str, op: str, event_type: str) -> bool:
    """
    time 叶是否需 SHAPE 小 LLM。

    明确结束线索已由规则处理则不调；开/关冲突或 create+time 且含「醒」类未进词表时调。
    """
    if (event_type or "").lower() != "time":
        return False
    if (op or "").strip().lower() == "end" or matches_end_cue(text):
        return False
    t = text or ""
    # 开/关线索冲突
    if matches_start_cue(t) and re.search(r"醒|结束|停|起床", t):
        return True
    # create+time 默认 start，但段内出现「醒」族（词表未覆盖的变体）
    if (op or "").strip().lower() in ("", "create") and re.search(
        r"醒", t
    ):
        return True
    return False


def _format_leaf_table(full_events: List[Dict[str, Any]]) -> str:
    """叶子事件短表注入 EVENT LLM。"""
    leaves = get_leaf_events(full_events or [])
    lines: List[str] = []
    for ev in leaves[:_MAX_EVENT_LINES]:
        eid = str(ev.get("event_id") or "").strip()
        ename = str(ev.get("event_name") or "").strip()
        if eid and ename:
            lines.append(f"{eid}\t{ename}")
    if len(leaves) > _MAX_EVENT_LINES:
        logger.info(
            "EVENT LLM 叶子表截断: total=%s cap=%s",
            len(leaves),
            _MAX_EVENT_LINES,
        )
    return "\n".join(lines) if lines else "(无叶子)"


async def llm_resolve_type(
    segment: str,
    llm_model: Dict[str, Any],
) -> Tuple[str, str, str, str, str, bool, List[str], str]:
    """
    TYPE 小 LLM（含 need_confirm / keywords / 预测两维）。

    Returns:
        (target_type, op, history_mode, predict_channel, time_answer,
         need_confirm, keywords, raw_summary)
    """
    cfg = llm_model_config_from_mapping(llm_model or {})
    content = await stream_llm_collect(
        messages=[
            {
                "role": "user",
                "content": f"段原文：{(segment or '').strip()}",
            }
        ],
        model_config=cfg,
        system_prompt=SEGMENT_TYPE_LLM_PROMPT,
        node_name="segment_type_llm",
    )
    data = _parse_json_obj(content or "")
    tt = str(data.get("target_type") or "").strip().lower()
    op = str(data.get("op") or "").strip().lower()
    hm = str(data.get("history_mode") or "").strip().lower()
    pc = str(data.get("predict_channel") or "").strip().lower()
    ta = str(data.get("time_answer") or "").strip().lower()
    need_confirm = bool(data.get("need_confirm"))
    raw_kws = data.get("keywords")
    keywords: List[str] = []
    if isinstance(raw_kws, list):
        for k in raw_kws:
            s = str(k or "").strip()
            if s and s not in keywords:
                keywords.append(s)
    allowed = {"feeding", "history", "predict", "conversation", "exit"}
    if tt not in allowed:
        tt = "feeding"
        op = op or "create"
        need_confirm = True
        pc, ta = "", ""
    if tt == "history":
        op = "read"
        if hm not in ("point", "daily"):
            hm = "point"
        pc, ta = "", ""
    elif tt == "predict":
        # 预测：清空 op/history_mode；两维非法则标需确认并清空（由调用方不写飞轮）
        op = ""
        hm = ""
        if pc not in ("active", "next") or ta not in ("clock", "remain"):
            pc, ta = "", ""
            need_confirm = True
    elif tt in ("conversation", "exit"):
        op = ""
        hm = ""
        pc, ta = "", ""
    else:
        if not op:
            op = "create"
        hm = hm if hm in ("point", "daily") else ""
        pc, ta = "", ""
    summary = json.dumps(
        {
            "target_type": tt,
            "op": op,
            "history_mode": hm,
            "predict_channel": pc,
            "time_answer": ta,
            "need_confirm": need_confirm,
            "keywords": keywords,
        },
        ensure_ascii=False,
    )
    return tt, op, hm, pc, ta, need_confirm, keywords, summary


async def llm_resolve_event(
    segment: str,
    full_events: List[Dict[str, Any]],
    llm_model: Dict[str, Any],
) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    EVENT 小 LLM：表内对齐；不确定返回 None。

    Returns:
        (event_dict_or_none, raw_summary)
    """
    table = _format_leaf_table(full_events)
    cfg = llm_model_config_from_mapping(llm_model or {})
    user = (
        f"段原文：{(segment or '').strip()}\n"
        f"叶子事件表（event_id\\tevent_name）：\n{table}"
    )
    content = await stream_llm_collect(
        messages=[{"role": "user", "content": user}],
        model_config=cfg,
        system_prompt=SEGMENT_EVENT_LLM_PROMPT,
        node_name="segment_event_llm",
    )
    data = _parse_json_obj(content or "")
    eid = str(data.get("event_id") or "").strip()
    ename = str(data.get("event_name") or "").strip()
    summary = json.dumps(
        {"event_id": eid, "event_name": ename},
        ensure_ascii=False,
    )
    if not eid:
        return None, summary
    # 必须落在表内
    for ev in full_events or []:
        if str(ev.get("event_id") or "") == eid:
            return ev, summary
    # id 对不上时尝试按名精确匹配叶子
    if ename:
        for ev in get_leaf_events(full_events or []):
            if str(ev.get("event_name") or "") == ename:
                return ev, summary
    logger.info("EVENT LLM 返回非表内 id，弃用: %s", summary)
    return None, summary


async def llm_resolve_time(
    segment: str,
    llm_model: Dict[str, Any],
) -> Tuple[Optional[int], Optional[int], str]:
    """
    TIME 小 LLM。

    Returns:
        (start_time, end_time, summary)；未解析则 (None, None, summary)
    """
    now = datetime.now(tz=_shanghai_tz())
    cfg = llm_model_config_from_mapping(llm_model or {})
    user = (
        f"当前时间（Asia/Shanghai）：{now.isoformat()}\n"
        f"段原文：{(segment or '').strip()}"
    )
    content = await stream_llm_collect(
        messages=[{"role": "user", "content": user}],
        model_config=cfg,
        system_prompt=SEGMENT_TIME_LLM_PROMPT,
        node_name="segment_time_llm",
    )
    data = _parse_json_obj(content or "")
    resolved = data.get("resolved")
    if resolved is False:
        return None, None, json.dumps(data, ensure_ascii=False)
    try:
        st = int(data.get("start_time") or 0)
        et = int(data.get("end_time") or 0)
    except (TypeError, ValueError):
        return None, None, json.dumps(data, ensure_ascii=False)
    if st <= 0 and et <= 0:
        return None, None, json.dumps(data, ensure_ascii=False)
    if et <= 0:
        et = st
    summary = json.dumps(
        {"start_time": st, "end_time": et},
        ensure_ascii=False,
    )
    return st, et, summary


async def llm_resolve_quantity(
    segment: str,
    llm_model: Dict[str, Any],
) -> Tuple[Optional[int], str]:
    """
    QTY 小 LLM。

    Returns:
        (quantity_or_none, summary)
    """
    cfg = llm_model_config_from_mapping(llm_model or {})
    content = await stream_llm_collect(
        messages=[
            {
                "role": "user",
                "content": f"段原文：{(segment or '').strip()}",
            }
        ],
        model_config=cfg,
        system_prompt=SEGMENT_QTY_LLM_PROMPT,
        node_name="segment_qty_llm",
    )
    data = _parse_json_obj(content or "")
    raw = data.get("quantity")
    summary = json.dumps({"quantity": raw}, ensure_ascii=False)
    if raw is None or raw == "":
        return None, summary
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return None, summary
    if n <= 0 or n > 100000:
        return None, summary
    return n, summary


async def llm_resolve_shape(
    segment: str,
    *,
    event_name: str,
    event_type: str,
    rule_op: str,
    rule_action: str,
    llm_model: Dict[str, Any],
) -> Tuple[str, str, str]:
    """
    SHAPE 小 LLM：裁定计时 op/action。

    Returns:
        (op, action, summary)；非法则回退 rule_op/rule_action
    """
    cfg = llm_model_config_from_mapping(llm_model or {})
    user = (
        f"段原文：{(segment or '').strip()}\n"
        f"已定事件：{(event_name or '').strip() or '计时事件'}"
        f"（type={(event_type or 'time').strip()}）\n"
        f"规则倾向：op={rule_op or 'create'}, action={rule_action or 'start'}"
    )
    content = await stream_llm_collect(
        messages=[{"role": "user", "content": user}],
        model_config=cfg,
        system_prompt=SEGMENT_SHAPE_LLM_PROMPT,
        node_name="segment_shape_llm",
    )
    data = _parse_json_obj(content or "")
    op = str(data.get("op") or "").strip().lower()
    action = str(data.get("action") or "").strip().lower()
    summary = json.dumps({"op": op, "action": action}, ensure_ascii=False)
    allowed = {
        ("create", "start"),
        ("end", "end"),
        ("create", "one"),
    }
    if (op, action) not in allowed:
        logger.info("SHAPE LLM 非法组合，回退规则: %s", summary)
        return (
            (rule_op or "create").strip().lower() or "create",
            (rule_action or "start").strip().lower() or "start",
            summary,
        )
    return op, action, summary

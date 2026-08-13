"""
查记录模板播报节点

业务说明：
按已定 event_ids + unix 窗 + 可选 remark 拉史，用模板填 content。
父 id 递归展开为叶子再拉史；来自父则塌成最近一条并点出父名与叶子名。
点查按 one/time/number 模板；日汇总先压缩。不调用历史答题 LLM。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.feeding.services.event_hierarchy import (
    get_descendant_leaves,
    get_event_by_id,
    is_parent_event,
)
from app.feeding.services.history_crud import infer_op, rewrite_standalone_document
from app.feeding.services.intent_cache_store import (
    intent_cache_store,
    last_cache_turn_store,
)
from app.shared.constants import IntentOp, TargetType
from app.shared.history_prompt_fields import (
    _parse_epoch,
    build_daily_history_summary,
    format_history_time,
)
from app.shared.history_window import resolve_window
from app.shared.http_client import http_client

logger = logging.getLogger(__name__)


def _row_name(row: Dict[str, Any]) -> str:
    return str(row.get("eventName") or row.get("event_name") or "")


def _row_id(row: Dict[str, Any]) -> str:
    return str(row.get("eventId") or row.get("event_id") or "")


def _row_remark(row: Dict[str, Any]) -> str:
    return str(row.get("remark") or "").strip()


def _row_start_ts(row: Dict[str, Any]) -> float:
    """排序键：startTime 越近越大。"""
    dt = _parse_epoch(row.get("startTime") or row.get("start_time"))
    return dt.timestamp() if dt is not None else 0.0


def _duration_seconds(row: Dict[str, Any]) -> Optional[int]:
    """计时：end-start 秒数；无效或未结束则 None。"""
    dt_s = _parse_epoch(row.get("startTime") or row.get("start_time"))
    dt_e = _parse_epoch(row.get("endTime") or row.get("end_time"))
    if dt_s is None or dt_e is None:
        return None
    secs = int((dt_e - dt_s).total_seconds())
    if secs < 0:
        return None
    return secs


def _format_duration_hm(secs: int) -> str:
    """秒数 → 用时口吻：X小时Y分 / Y分 / 不到1分钟。"""
    if secs < 60:
        return "不到1分钟"
    hours, rem = divmod(secs, 3600)
    minutes = rem // 60
    if hours and minutes:
        return f"{hours}小时{minutes}分"
    if hours:
        return f"{hours}小时"
    return f"{minutes}分"


def _lookup_event_type(
    row: Dict[str, Any],
    full_events: List[Dict[str, Any]],
) -> str:
    """
    解析 one|time|number。

    优先历史行 eventType；缺省按字典 event_type。
    """
    t = str(row.get("eventType") or row.get("event_type") or "").strip().lower()
    if t in ("number", "time", "one"):
        return t
    found = get_event_by_id(_row_id(row), full_events)
    if found:
        t2 = str(found.get("event_type") or "").strip().lower()
        if t2 in ("number", "time", "one"):
            return t2
    return "one"


def _remark_suffix(row: Dict[str, Any]) -> str:
    remark = _row_remark(row)
    return f"，备注{remark}" if remark else ""


def _format_typed_clause(
    *,
    name: str,
    row: Dict[str, Any],
    kind: str,
    when: str,
    parent_name: str = "",
) -> str:
    """
    按事件类型拼一句点查。

    叶子：上一次{名}是{相对时间}…
    父：上一次{父}的时候是{叶}，{相对时间}…
    """
    extra_remark = _remark_suffix(row)
    if parent_name:
        head = f"上一次{parent_name}的时候是{name}，{when}"
    else:
        head = f"上一次{name}是{when}"
    if kind == "time":
        secs = _duration_seconds(row)
        if secs is None:
            if parent_name:
                return f"上一次{parent_name}的时候是{name}，{when}开始的，现在正在进行中{extra_remark}"
            return f"上一次{name}是{when}开始的，现在正在进行中{extra_remark}"
        return f"{head}，用时{_format_duration_hm(secs)}{extra_remark}"
    if kind == "number":
        num = row.get("eventNumber")
        if num is None:
            num = row.get("event_number")
        if num in (None, ""):
            num = 0
        return f"{head}，数量为：{num}{extra_remark}"
    # 一次性：不带 number
    return f"{head}{extra_remark}"


def _expand_query_ids(
    event_ids: List[str],
    full_events: List[Dict[str, Any]],
) -> Tuple[List[str], List[str]]:
    """
    把父 id 展开成子孙叶子 id。

    Returns:
        (拉史用叶子 id 列表, 原始列表中的父 id)
    """
    parent_ids: List[str] = []
    query_ids: List[str] = []
    seen: set[str] = set()
    for eid in event_ids:
        if is_parent_event(eid, full_events):
            parent_ids.append(eid)
            for leaf in get_descendant_leaves(eid, full_events):
                lid = str(leaf.get("event_id") or "")
                if lid and lid not in seen:
                    seen.add(lid)
                    query_ids.append(lid)
            continue
        if eid not in seen:
            seen.add(eid)
            query_ids.append(eid)
    return query_ids, parent_ids


def _template_point(
    rows: List[Dict[str, Any]],
    event_names: List[str],
    full_events: List[Dict[str, Any]],
) -> str:
    """多叶子分别点查：每事件最近一条，按类型模板。"""
    by_name: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        name = _row_name(row)
        if name and name not in by_name:
            by_name[name] = row
    parts: List[str] = []
    wanted = event_names or list(by_name.keys())
    for name in wanted:
        row = by_name.get(name)
        if not row:
            parts.append(f"没有记到{name}")
            continue
        when = format_history_time(
            row.get("startTime") or row.get("start_time"),
            style="relative",
        ) or "未知时间"
        kind = _lookup_event_type(row, full_events)
        parts.append(_format_typed_clause(name=name, row=row, kind=kind, when=when))
    return "。".join(parts) + "。" if parts else "没有查到相关记录。"


def _template_parent_latest(
    rows: List[Dict[str, Any]],
    parent_name: str,
    full_events: List[Dict[str, Any]],
) -> str:
    """父点查：子孙叶子里取 startTime 最近一条，点出父名与叶子名。"""
    if not rows:
        return f"没有记到{parent_name}相关记录。"
    latest = max(rows, key=_row_start_ts)
    leaf_name = _row_name(latest) or "该记录"
    when = format_history_time(
        latest.get("startTime") or latest.get("start_time"),
        style="relative",
    ) or "未知时间"
    kind = _lookup_event_type(latest, full_events)
    return (
        _format_typed_clause(
            name=leaf_name,
            row=latest,
            kind=kind,
            when=when,
            parent_name=parent_name,
        )
        + "。"
    )


async def speak_history(state: Dict[str, Any]) -> Dict[str, Any]:
    """拉史并模板播报。"""
    intent = dict(state.get("intent_result") or {})
    op = infer_op(intent)
    if op != IntentOp.READ.value and intent.get("target_type") != TargetType.HISTORY.value:
        return {}
    device_no = state.get("device_no") or ""
    event_ids = intent.get("event_ids") or []
    if not event_ids and intent.get("event_id"):
        event_ids = [intent.get("event_id")]
    original_ids = [str(x) for x in event_ids if x not in (None, "")]
    remark = (intent.get("remark_keyword") or state.get("remark_keyword") or "").strip()
    req = {
        "start_time": intent.get("start_time") or intent.get("startTime"),
        "end_time": intent.get("end_time") or intent.get("endTime"),
        "time_range": intent.get("time_range"),
    }
    start_time, end_time = resolve_window(req)
    # 点查必须有事件；否则只确认不拉全量
    if not original_ids:
        content = "请先说明要查哪个事件，我不会一次拉取全部记录。"
        intent["content"] = content
        return {"intent_result": intent, "response": content}
    full_events = (
        state.get("event_dictionary_full") or state.get("event_dictionary") or []
    )
    query_ids, parent_ids = _expand_query_ids(original_ids, full_events)
    # 父下面没有叶子时仍按原 id 拉，避免空 filter 变成全类型
    fetch_ids = query_ids or original_ids
    try:
        rows = await http_client.get_filtered_history_events(
            device_no=device_no,
            event_ids=fetch_ids,
            start_time=start_time,
            end_time=end_time,
            limit=int(intent.get("limit") or 20),
            remark=remark or None,
        )
    except Exception as exc:
        logger.error(f"查记录拉史失败: {exc}", exc_info=True)
        intent["content"] = "暂时没查到历史记录，请稍后再试。"
        return {"intent_result": intent, "response": intent["content"]}
    mode = (intent.get("history_mode") or "point").strip()
    id_to_name = {
        str(e.get("event_id")): e.get("event_name") or "" for e in full_events
    }
    # 仅原始 id 全是父时塌成最近一条；显式多叶子仍分别播报
    collapse_parent = bool(parent_ids) and all(
        is_parent_event(eid, full_events) for eid in original_ids
    )
    if mode == "daily":
        content = build_daily_history_summary(rows) or "这段时间没有相关记录。"
    elif collapse_parent:
        parent_name = (
            intent.get("event_name")
            or id_to_name.get(parent_ids[0], "")
            or "该分类"
        )
        content = _template_parent_latest(rows or [], str(parent_name), full_events)
    else:
        names = []
        for eid in original_ids:
            names.append(id_to_name.get(str(eid)) or "")
        names = [n for n in names if n]
        content = _template_point(rows or [], names, full_events)
    intent["op"] = IntentOp.READ.value
    intent["content"] = content
    # 缓存存原始 id（父则存父），命中后再展开
    cache_event_id = intent.get("event_id") or (
        original_ids[0] if original_ids else ""
    )
    cache_event_name = intent.get("event_name") or id_to_name.get(
        str(cache_event_id), ""
    )
    intent_cache_store.add(
        rewrite_standalone_document(intent, state.get("user_input") or ""),
        {
            "op": IntentOp.READ.value,
            "target_type": TargetType.HISTORY.value,
            "action": "search",
            "event_id": cache_event_id,
            "event_name": cache_event_name,
            "event_ids": original_ids,
            "events": intent.get("events") or [],
            "remark_keyword": remark,
            "start_time": start_time,
            "end_time": end_time,
        },
    )
    # 缓存免确认执行成功后记下短窗，便于下一句同一问扣分
    if state.get("intent_cache_hit"):
        last_cache_turn_store.remember(
            device_no,
            state.get("user_input") or "",
            str(state.get("matched_vector_id") or ""),
        )
    logger.info(f"查记录模板: {content[:80]}")
    return {"intent_result": intent, "response": content, "history_events": rows or []}

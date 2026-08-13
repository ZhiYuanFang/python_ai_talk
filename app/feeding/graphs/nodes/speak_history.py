"""
查记录模板播报节点

业务说明：
按已定 event_ids + unix 窗 + 可选 remark 拉史，用模板填 content。
点查每条带备注；日汇总先压缩。不调用历史答题 LLM。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.feeding.services.history_crud import infer_op, rewrite_standalone_document
from app.feeding.services.intent_cache_store import intent_cache_store
from app.shared.constants import IntentOp, TargetType
from app.shared.history_prompt_fields import (
    build_daily_history_summary,
    format_history_time,
)
from app.shared.history_window import resolve_window
from app.shared.http_client import http_client

logger = logging.getLogger(__name__)


def _row_name(row: Dict[str, Any]) -> str:
    return str(row.get("eventName") or row.get("event_name") or "该事件")


def _row_remark(row: Dict[str, Any]) -> str:
    return str(row.get("remark") or "").strip()


def _template_point(rows: List[Dict[str, Any]], event_names: List[str]) -> str:
    """点查模板：每事件最近一条，带备注。"""
    by_name: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        name = _row_name(row)
        if name not in by_name:
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
        qty = row.get("eventNumber") or row.get("event_number")
        unit = row.get("eventUnit") or row.get("event_unit") or ""
        qty_txt = f"{qty}{unit}" if qty not in (None, "", 0) else ""
        remark = _row_remark(row)
        extra = ""
        if qty_txt:
            extra += f"，{qty_txt}"
        if remark:
            extra += f"，备注{remark}"
        parts.append(f"上一次{name}是{when}{extra}")
    return "。".join(parts) + "。" if parts else "没有查到相关记录。"


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
    event_ids = [str(x) for x in event_ids if x not in (None, "")]
    remark = (intent.get("remark_keyword") or state.get("remark_keyword") or "").strip()
    req = {
        "start_time": intent.get("start_time") or intent.get("startTime"),
        "end_time": intent.get("end_time") or intent.get("endTime"),
        "time_range": intent.get("time_range"),
    }
    start_time, end_time = resolve_window(req)
    # 点查必须有事件；否则只确认不拉全量
    if not event_ids:
        content = "请先说明要查哪个事件，我不会一次拉取全部记录。"
        intent["content"] = content
        return {"intent_result": intent, "response": content}
    try:
        rows = await http_client.get_filtered_history_events(
            device_no=device_no,
            event_ids=event_ids,
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
    names = []
    dictionary = state.get("event_dictionary") or []
    id_to_name = {
        str(e.get("event_id")): e.get("event_name") or "" for e in dictionary
    }
    for eid in event_ids:
        names.append(id_to_name.get(str(eid)) or "")
    names = [n for n in names if n]
    if mode == "daily":
        content = build_daily_history_summary(rows) or "这段时间没有相关记录。"
    else:
        content = _template_point(rows or [], names)
    intent["op"] = IntentOp.READ.value
    intent["content"] = content
    intent_cache_store.add(
        rewrite_standalone_document(intent, state.get("user_input") or ""),
        {
            "op": IntentOp.READ.value,
            "target_type": TargetType.HISTORY.value,
            "action": "search",
            "event_id": intent.get("event_id"),
            "event_name": intent.get("event_name"),
            "event_ids": event_ids,
            "events": intent.get("events") or [],
            "remark_keyword": remark,
        },
    )
    logger.info(f"查记录模板: {content[:80]}")
    return {"intent_result": intent, "response": content, "history_events": rows or []}

"""
批量落库节点

业务说明：
已确认的 create/update/delete/end 走一条 batch，
用模板填写 content，落库成功后按段写事件短说法（直执行路径同样写入）。
仅对 update/delete 子项现查 latest；create/end 不因无记录而跳过。
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.feeding.schemas.intent_result import IntentResult, coerce_intent_result
from app.feeding.services.closed_interval import apply_time_slots_to_events
from app.feeding.services.history_crud import (
    collect_event_items,
    execute_batch,
    infer_route_kind,
    render_persist_content,
    sort_end_items_first,
)
from app.feeding.services.intent_cache_store import intent_cache_store
from app.feeding.services.intent_events import normalize_intent_events
from app.shared.constants import IntentOp
from app.shared.graphs.state_patch import state_get

logger = logging.getLogger(__name__)


async def execute_history_crud(state: Any) -> Dict[str, Any]:
    """
    执行批量 CRUD 并回执。

    未确认不进本节点（由图路由保证）。
    落库前再跑一轮钟点/时长覆盖，保证分类路径也能闭合补记。
    """
    intent = coerce_intent_result(state_get(state, "intent_result")).to_plain_dict()
    intent = normalize_intent_events(intent)
    if state_get(state, "need_confirm"):
        return {}
    if infer_route_kind(intent) != "cud":
        return {}
    device_no = state_get(state, "device_no") or ""
    full_events = (
        state_get(state, "event_dictionary_full")
        or state_get(state, "event_dictionary")
        or []
    )
    # 分类路径未走 overlay 时，仍用原文补全闭合起止
    text = state_get(state, "user_input") or state_get(state, "text") or ""
    events = [e for e in (intent.get("events") or []) if isinstance(e, dict)]
    new_events, slot_changed = apply_time_slots_to_events(text, events)
    if slot_changed:
        intent["events"] = new_events
        logger.info("落库前闭合槽位已覆盖: events=%s", len(new_events))
    items, missing = collect_event_items(intent, full_events)
    items = sort_end_items_first(items)
    intent["missing_events"] = missing

    # 仅 update/delete 现查 latest；create/end 保持 id=0
    items = await _fill_latest_ids_for_mutations(device_no, items)

    skip_fails = []
    runnable = []
    for it in items:
        item_op = (it.get("_item_op") or it.get("op") or "").strip().lower()
        needs_id = item_op in (IntentOp.UPDATE.value, IntentOp.DELETE.value)
        if it.get("_skip_reason") or (needs_id and int(it.get("id") or 0) <= 0):
            skip_fails.append(
                {
                    "index": len(runnable) + len(skip_fails),
                    "ok": False,
                    "reason": it.get("_skip_reason") or "没有找到可操作的记录",
                    "_display_name": it.get("_display_name"),
                }
            )
        else:
            runnable.append(it)
    items = runnable
    if not items:
        merged_items = [
            {
                "_display_name": sf.get("_display_name") or "事件",
                "op": "update",
            }
            for sf in skip_fails
        ]
        content = render_persist_content(merged_items, skip_fails, missing)
        intent["content"] = content
        return {"intent_result": IntentResult.model_validate(intent), "response": content}
    try:
        results = await execute_batch(device_no, items) if items else []
    except Exception as exc:
        logger.error(f"batch 失败: {exc}", exc_info=True)
        results = [
            {"index": i, "ok": False, "reason": str(exc)} for i in range(len(items))
        ]
    merged_items = list(items)
    merged_results = list(results)
    for sf in skip_fails:
        merged_items.append(
            {"_display_name": sf.get("_display_name") or "事件", "op": "update"}
        )
        merged_results.append(sf)
    content = render_persist_content(merged_items, merged_results, missing)
    intent["content"] = content
    # 仅成功子项写短说法（失败段不写；不依赖 leaf_confirm）
    ok_eids: set[str] = set()
    for i, it in enumerate(items):
        res = {}
        for r in results:
            if int(r.get("index", -1)) == i:
                res = r
                break
        if not res and i < len(results):
            res = results[i] or {}
        if not bool(res.get("ok")):
            continue
        eid = str(it.get("eventId") or it.get("event_id") or "").strip()
        if eid:
            ok_eids.add(eid)
    if ok_eids:
        from app.feeding.services.event_hierarchy import is_parent_event

        full = state_get(state, "event_dictionary_full") or []
        for ev in intent.get("events") or []:
            if not isinstance(ev, dict):
                continue
            eid = str(ev.get("event_id") or "").strip()
            if not eid or eid not in ok_eids:
                continue
            seg = str(ev.get("segment_text") or "").strip()
            ename = str(ev.get("event_name") or "").strip()
            doc = seg or ename
            if not doc:
                continue
            kind = "parent" if is_parent_event(eid, full) else "leaf"
            intent_cache_store.add_event_phrase(
                doc, event_id=eid, event_name=ename, kind=kind
            )
    logger.info(f"落库回执: {content}")
    return {"intent_result": IntentResult.model_validate(intent), "response": content}


async def _fill_latest_ids_for_mutations(
    device_no: str, items: list
) -> list:
    """仅对 update/delete 且无 id 的项，按 eventId 拉最近一条。"""
    from app.shared.http_client import http_client

    filled = []
    for it in items:
        item_op = (it.get("_item_op") or it.get("op") or "").strip().lower()
        if item_op not in (IntentOp.UPDATE.value, IntentOp.DELETE.value):
            filled.append(it)
            continue
        if int(it.get("id") or 0) > 0:
            filled.append(it)
            continue
        eid = it.get("eventId")
        if not eid:
            it["_skip_reason"] = "没有事件ID，无法定位记录"
            filled.append(it)
            continue
        try:
            rows = await http_client.get_filtered_history_events(
                device_no=device_no,
                event_ids=[str(eid)],
                limit=1,
            )
        except Exception as exc:
            logger.warning(f"现查 latest 失败: {exc}")
            rows = []
        if not rows:
            it["id"] = 0
            it["_skip_reason"] = "没有找到可改/删的最近记录"
            filled.append(it)
            continue
        hid = rows[0].get("id") or rows[0].get("Id")
        try:
            it["id"] = int(hid)
        except (TypeError, ValueError):
            it["id"] = 0
        if item_op == IntentOp.UPDATE.value and not it.get("eventNumber"):
            it["eventNumber"] = int(
                rows[0].get("eventNumber") or rows[0].get("event_number") or 0
            )
        filled.append(it)
    return filled

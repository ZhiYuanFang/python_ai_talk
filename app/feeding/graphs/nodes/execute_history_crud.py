"""
批量落库节点

业务说明：
已确认（或高置信免确认）的 create/update/delete/end 走一条 batch，
用模板填写 content，成功后写意图缓存。
仅对 update/delete 子项现查 latest；create/end 不因无记录而跳过。
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.feeding.schemas.intent_result import IntentResult, coerce_intent_result
from app.feeding.services.history_crud import (
    collect_event_items,
    execute_batch,
    infer_route_kind,
    render_persist_content,
    rewrite_standalone_document,
    sort_end_items_first,
)
from app.feeding.services.intent_cache_store import (
    intent_cache_store,
    last_cache_turn_store,
)
from app.feeding.services.intent_events import normalize_intent_events
from app.shared.constants import IntentOp
from app.shared.graphs.state_patch import state_get

logger = logging.getLogger(__name__)


async def execute_history_crud(state: Any) -> Dict[str, Any]:
    """
    执行批量 CRUD 并回执。

    未确认不进本节点（由图路由保证）。
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
    any_ok = any(bool(r.get("ok")) for r in results)
    if any_ok:
        doc = rewrite_standalone_document(
            intent, state_get(state, "user_input") or ""
        )
        intent_cache_store.add(
            doc,
            {
                "target_type": intent.get("target_type"),
                "events": intent.get("events") or [],
                "remark_keyword": intent.get("remark_keyword"),
            },
        )
        if state_get(state, "intent_cache_hit"):
            last_cache_turn_store.remember(
                device_no,
                state_get(state, "user_input") or "",
                str(state_get(state, "matched_vector_id") or ""),
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

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
    # 分类路径未走 overlay 时，仍用原文补全闭合起止。删除不靠钟点选行，不把时间盖上去
    text = state_get(state, "user_input") or state_get(state, "text") or ""
    events = [e for e in (intent.get("events") or []) if isinstance(e, dict)]
    slot_targets = [
        e
        for e in events
        if str(e.get("op") or "").strip().lower() != IntentOp.DELETE.value
    ]
    new_targets, slot_changed = apply_time_slots_to_events(text, slot_targets)
    if slot_changed:
        filled = iter(new_targets)
        new_events = [
            next(filled)
            if str(e.get("op") or "").strip().lower() != IntentOp.DELETE.value
            else e
            for e in events
        ]
    else:
        new_events = events
    if slot_changed:
        intent["events"] = new_events
        logger.info("落库前闭合槽位已覆盖: events=%s", len(new_events))
    # U·end：无进行中计时则转 C（create）；time 无闭合起止则追问
    intent, end_clarify = await _rewrite_end_without_open(
        device_no, intent, full_events
    )
    if end_clarify:
        intent["content"] = end_clarify
        intent["need_confirm"] = True
        return {
            "intent_result": IntentResult.model_validate(intent),
            "response": end_clarify,
            "need_confirm": True,
        }
    items, missing = collect_event_items(intent, full_events)
    items = sort_end_items_first(items)
    intent["missing_events"] = missing

    # 仅本批含修改或删除时才解析定位；记一笔的钟点已在段解析写入，不按 latest 改旧记录
    locate_strategy = "latest"
    mutation_ops = [
        (it.get("_item_op") or it.get("op") or "").strip().lower()
        for it in items
        if isinstance(it, dict)
    ]
    mutation_ops = [
        op
        for op in mutation_ops
        if op in (IntentOp.UPDATE.value, IntentOp.DELETE.value)
    ]
    delete_only = bool(mutation_ops) and all(
        op == IntentOp.DELETE.value for op in mutation_ops
    )
    if delete_only:
        # 纯删除：有定位词用本地结果，没有就直接最近一条，不问模型
        from app.feeding.services.dim_local_rules import match_local_locate
        from app.feeding.services.dim_rule_lexicon import apply_locate_view
        from app.feeding.services.event_homophone import cut_segment_pinyin

        local_locate = match_local_locate(
            apply_locate_view(text, cut_segment_pinyin(text))
        )
        if local_locate:
            locate_strategy = local_locate
            logger.info("纯删除本地定位: strategy=%s", local_locate)
        else:
            locate_strategy = "latest"
            logger.info("纯删除无定位词，直接最近一条")
    elif mutation_ops:
        try:
            from app.feeding.services.dim_resolve import resolve_locate

            locate_strategy, _need_loc = await resolve_locate(
                text, llm_model=state_get(state, "llm_model") or {}
            )
        except Exception as exc:
            logger.warning("定位策略解析失败，回退 latest: %s", exc)
    items = await _fill_latest_ids_for_mutations(
        device_no, items, strategy=locate_strategy
    )

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
            if ev.get("history_guessed"):
                continue
            kind = "parent" if is_parent_event(eid, full) else "leaf"
            intent_cache_store.add_event_phrase(
                doc, event_id=eid, event_name=ename, kind=kind
            )
        # 史已变：清除预测算法 Redis 快照，避免连续兜底用旧间隔
        try:
            from app.feeding.services.predict_algo_cache import predict_algo_cache

            await predict_algo_cache.delete(device_no)
        except Exception as exc:
            logger.warning("清除预测算法快照失败: %s", exc)
    logger.info(f"落库回执: {content}")
    return {"intent_result": IntentResult.model_validate(intent), "response": content}


async def _rewrite_end_without_open(
    device_no: str,
    intent: Dict[str, Any],
    full_events: list,
) -> tuple:
    """
    计时 U·end 无进行中 → 转补记。非计时不查进行中、不改成新建。

    Returns:
        (intent, clarify_message|None)
    """
    from app.feeding.graphs.nodes.remark_probe import _is_open_end
    from app.feeding.services.event_hierarchy import get_event_by_id
    from app.shared.constants import IntentAction, IntentOp, TargetType
    from app.shared.history_window import enum_to_unix
    from app.shared.http_client import http_client

    def _event_type(item: Dict[str, Any]) -> str:
        eid = str(item.get("event_id") or "").strip()
        leaf = get_event_by_id(eid, full_events) if eid else None
        return str(
            (leaf or {}).get("event_type")
            or (leaf or {}).get("type")
            or item.get("event_type")
            or "one"
        ).lower()

    events = [e for e in (intent.get("events") or []) if isinstance(e, dict)]
    timer_ends = [
        e
        for e in events
        if str(e.get("op") or "").lower() == "end" and _event_type(e) == "time"
    ]
    if not timer_ends:
        return intent, None
    start_time, end_time = enum_to_unix("last_30_days")
    try:
        rows = await http_client.get_filtered_history_events(
            device_no=device_no,
            event_ids=None,
            start_time=start_time,
            end_time=end_time,
            limit=50,
        )
    except Exception as exc:
        logger.warning("U·end 查进行中失败: %s", exc)
        rows = []
    open_by_eid = set()
    for row in rows or []:
        if not _is_open_end(row):
            continue
        eid = str(row.get("eventId") or row.get("event_id") or "").strip()
        if eid:
            open_by_eid.add(eid)
    rewritten: list = []
    clarify_parts: list = []
    rewrote = False
    for ev in events:
        item = dict(ev)
        if str(item.get("op") or "").lower() != "end":
            rewritten.append(item)
            continue
        et = _event_type(item)
        if et != "time":
            # 非计时保持原操作，不因没有进行中改成新建
            rewritten.append(item)
            continue
        eid = str(item.get("event_id") or "").strip()
        if eid and eid in open_by_eid:
            rewritten.append(item)
            continue
        # 计时无进行中 → 转补记
        item["op"] = IntentOp.CREATE.value
        rewrote = True
        try:
            st = int(item.get("start_time") or 0)
            etm = int(item.get("end_time") or 0)
        except (TypeError, ValueError):
            st, etm = 0, 0
        if et == "time":
            if st > 0 and etm > st:
                item["action"] = IntentAction.ONE.value
            else:
                name = str(item.get("event_name") or "该计时")
                clarify_parts.append(f"{name}需要补充开始和结束时间")
                rewritten.append(item)
                continue
        rewritten.append(item)
        logger.info("计时 end 无进行中，转补记: event_id=%s", eid)
    out = dict(intent)
    out["events"] = rewritten
    if rewrote:
        out["target_type"] = TargetType.CREATE.value
    if clarify_parts:
        return out, "。".join(clarify_parts) + "。"
    return out, None


def _pick_row_by_strategy(rows: list, strategy: str) -> Any:
    """按定位策略选一行；不含 historyId 持久化。"""
    from app.feeding.graphs.nodes.remark_probe import _is_open_end

    if not rows:
        return None
    st = (strategy or "latest").strip().lower()
    if st == "open_timer":
        opens = [r for r in rows if _is_open_end(r)]
        return opens[0] if opens else None
    if st == "prefer_completed":
        completed = [r for r in rows if not _is_open_end(r)]
        return completed[0] if completed else rows[0]
    return rows[0]


async def _fill_latest_ids_for_mutations(
    device_no: str, items: list, *, strategy: str = "latest"
) -> list:
    """仅对 update/delete 且无 id 的项，按策略现查选行。"""
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
                limit=10,
            )
        except Exception as exc:
            logger.warning(f"现查定位失败: {exc}")
            rows = []
        row = _pick_row_by_strategy(rows or [], strategy)
        if not row:
            it["id"] = 0
            it["_skip_reason"] = "没有找到可改/删的最近记录"
            filled.append(it)
            continue
        hid = row.get("id") or row.get("Id")
        try:
            it["id"] = int(hid)
        except (TypeError, ValueError):
            it["id"] = 0
        if item_op == IntentOp.UPDATE.value and not it.get("eventNumber"):
            it["eventNumber"] = int(
                row.get("eventNumber") or row.get("event_number") or 0
            )
        filled.append(it)
    return filled

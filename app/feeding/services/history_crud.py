"""
喂养历史批量落库与模板回执

业务说明：
确认后一次调用 Go batch；按结果拼用户可感知的 content。
禁止新建事件类型；字典外名称进 missing_events。
结束计时只交 eventId + action=end，不查进行中、不填 history_id。
落库前按字典 event_type 盖时间：非计时 endTime=startTime。
同一 batch 先 end 后 create。
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from app.feeding.services.event_hierarchy import get_event_by_id
from app.shared.constants import IntentAction, IntentOp
from app.shared.http_client import http_client

logger = logging.getLogger(__name__)


def infer_op(intent: Dict[str, Any]) -> str:
    """从 op 或 action 推断 CRUD 轴。"""
    op = (intent.get("op") or "").strip().lower()
    if op in {
        IntentOp.CREATE.value,
        IntentOp.READ.value,
        IntentOp.UPDATE.value,
        IntentOp.DELETE.value,
    }:
        return op
    action = (intent.get("action") or "").strip().lower()
    if action in (
        IntentAction.START.value,
        IntentAction.END.value,
        IntentAction.ONE.value,
        IntentAction.MULTI.value,
    ):
        return IntentOp.CREATE.value
    if action == IntentAction.SEARCH.value:
        return IntentOp.READ.value
    return ""


def _is_timer_leaf(leaf: Dict[str, Any]) -> bool:
    """
    是否为计时事件：只认字典 event_type=time。

    业务说明：缺省或 one/number 一律当非计时，避免被记成进行中。
    不采信 LLM 返回的 event_type。
    """
    return str(leaf.get("event_type") or "").strip().lower() == "time"


def sort_end_items_first(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    同一 batch 先提交 end，再提交其余项。

    业务说明：停爬再开坐时必须先结束，不依赖模型 events[] 顺序。
    """
    ends = [it for it in items if (it.get("op") or "") == "end"]
    rest = [it for it in items if (it.get("op") or "") != "end"]
    return ends + rest


def collect_event_items(
    intent: Dict[str, Any],
    full_events: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    从意图结果收集可落库子项；字典外名称进 missing。

    业务逻辑：
    - action=end 且字典为计时：op=end，history id 固定 0，不查 latest。
    - 非计时 create：endTime=startTime，即使模型写了 start/end。
    - 计时且非 end：create 且 endTime=0（进行中）。
    - 返回前把 end 项排到 create 前面。

    Returns:
        (items, missing_names)
    """
    missing: List[str] = []
    items: List[Dict[str, Any]] = []
    raw_events = intent.get("events") or []
    if not raw_events:
        raw_events = [
            {
                "action": intent.get("action") or IntentAction.ONE.value,
                "event_id": intent.get("event_id") or "",
                "event_name": intent.get("event_name") or "",
                "quantity": intent.get("quantity"),
                "history_id": intent.get("history_id"),
                "remark": intent.get("remark"),
            }
        ]
    op = infer_op(intent) or IntentOp.CREATE.value
    now = int(time.time())
    for ev in raw_events:
        if not isinstance(ev, dict):
            continue
        name = str(ev.get("event_name") or "").strip()
        eid = str(ev.get("event_id") or "").strip()
        leaf = get_event_by_id(eid, full_events) if eid else None
        if not leaf and name:
            missing.append(name)
            continue
        if not leaf:
            if name:
                missing.append(name)
            continue
        action = str(
            ev.get("action") or intent.get("action") or IntentAction.ONE.value
        ).strip().lower()
        # 计时与否只认字典，忽略意图里 LLM 填的 event_type
        is_timer = _is_timer_leaf(leaf)
        item_op = op
        if action == IntentAction.END.value:
            if is_timer:
                # Go 按 eventId 结束最近一条，Python 不填 history_id
                item_op = "end"
            elif op in (IntentOp.CREATE.value, ""):
                # 非计时不能当计时结束，当成瞬时记录
                item_op = "create"
        qty = ev.get("quantity")
        if qty is None:
            qty = intent.get("quantity")
        try:
            number = int(qty) if qty is not None else 0
        except (TypeError, ValueError):
            number = 0
        normalized_op = item_op if item_op != IntentOp.CREATE.value else "create"
        start_time = int(ev.get("start_time") or now)
        if normalized_op == "end":
            # 结束时间由 Go 补最近一条，Python 不填
            hid_int = 0
            end_time = 0
        elif normalized_op == "create":
            hid_int = 0
            # 非计时（one/number/缺省）结束时间必须等于开始时间
            end_time = 0 if is_timer else start_time
        else:
            hid = ev.get("history_id")
            try:
                hid_int = int(hid) if hid not in (None, "") else 0
            except (TypeError, ValueError):
                hid_int = 0
            end_time = int(ev.get("end_time") or 0)
        items.append(
            {
                "op": normalized_op,
                "action": action,
                "id": hid_int,
                "eventId": int(str(leaf.get("event_id") or eid) or 0),
                "eventName": leaf.get("event_name") or name,
                "eventUnit": leaf.get("event_unit") or ev.get("event_unit") or "",
                "eventNumber": number,
                "startTime": start_time,
                "endTime": end_time,
                "remark": str(ev.get("remark") or intent.get("remark") or ""),
                "_display_name": leaf.get("event_name") or name,
            }
        )
    return sort_end_items_first(items), missing


async def execute_batch(
    device_no: str,
    items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """调用 Go batch，返回 results。"""
    payload = []
    for it in items:
        payload.append({k: v for k, v in it.items() if not str(k).startswith("_")})
    return await http_client.batch_history_events(device_no, payload)


def render_persist_content(
    items: List[Dict[str, Any]],
    results: List[Dict[str, Any]],
    missing: List[str],
) -> str:
    """
    模板回执：全成功 / 部分成功 / 全失败。

    业务说明：必须让用户感知入库结果，不用 LLM 编话。
    """
    ok_lines: List[str] = []
    fail_lines: List[str] = []
    for i, item in enumerate(items):
        name = item.get("_display_name") or item.get("eventName") or "事件"
        qty = item.get("eventNumber") or 0
        unit = item.get("eventUnit") or ""
        op = item.get("op") or "create"
        res = {}
        for r in results:
            if int(r.get("index", -1)) == i:
                res = r
                break
        if not res and i < len(results):
            res = results[i] or {}
        ok = bool(res.get("ok"))
        reason = str(res.get("reason") or "").strip()
        qty_txt = f"{qty}{unit}" if qty else ""
        if ok:
            if op in ("create",):
                ok_lines.append(f"已记录{name}" + (f" {qty_txt}" if qty_txt else ""))
            elif op == "update":
                ok_lines.append(f"已修改{name}" + (f" 为 {qty_txt}" if qty_txt else ""))
            elif op == "delete":
                ok_lines.append(f"已删除{name}")
            elif op == "end":
                ok_lines.append(f"已结束{name}")
            else:
                ok_lines.append(f"{name}操作成功")
        else:
            fail_lines.append(f"{name}未入库，因为{reason or '接口失败'}")
    for name in missing:
        fail_lines.append(f"{name}未入库，因为不是已有事件（不会新建事件类型）")
    parts = ok_lines + fail_lines
    if not parts:
        return "没有可执行的事件操作。"
    return "。".join(parts) + "。"


def rewrite_standalone_document(intent: Dict[str, Any], original: str) -> str:
    """
    把本轮成功意图改写成可缓存的独立句。

    不用「嗯/是的」当 document。
    """
    names = []
    for ev in intent.get("events") or []:
        n = (ev.get("event_name") or "").strip()
        if n:
            names.append(n)
    if not names and intent.get("event_name"):
        names.append(str(intent.get("event_name")))
    op = infer_op(intent)
    remark = (intent.get("remark_keyword") or "").strip()
    joined = "、".join(names) if names else (original or "").strip()
    if op == IntentOp.READ.value:
        if remark:
            return f"上一次{joined}备注{remark}是什么时候"
        return f"上一次{joined}是什么时候"
    if op == IntentOp.UPDATE.value:
        return f"把{joined}改一下"
    if op == IntentOp.DELETE.value:
        return f"删除刚才的{joined}"
    src = (original or "").strip()
    if src and src not in {"嗯", "是的", "好的", "1"}:
        return src
    return f"记录{joined}" if joined else src

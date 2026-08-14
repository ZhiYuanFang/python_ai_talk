"""
喂养历史批量落库与模板回执

业务说明：
确认后一次调用 Go batch；按结果拼用户可感知的 content。
子项 op 为权威；禁止顶层 op 广播。
结束计时只交 eventId + op=end；仅 update/delete 现查 latest。
同一 batch 先 end 后其余。
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Tuple

from app.feeding.services.event_hierarchy import get_event_by_id
from app.feeding.services.intent_events import (
    CUD_OPS,
    derive_item_op,
    event_ops,
    has_read_events,
    normalize_intent_events,
)
from app.shared.constants import IntentAction, IntentOp
from app.shared.http_client import http_client

logger = logging.getLogger(__name__)


def infer_route_kind(intent: Dict[str, Any]) -> str:
    """
    由图路由使用：read | cud | ""。

    基于 normalize 后的 events[].op，不读顶层 op/action。
    """
    data = normalize_intent_events(dict(intent))
    if has_read_events(data):
        return IntentOp.READ.value
    if event_ops(data) & CUD_OPS:
        return "cud"
    return ""


def infer_op(intent: Dict[str, Any]) -> str:
    """
    兼容旧调用：从子项推导一个代表 op。

    有 read → read；否则取首个 CUD 代表值；再否则空。
    """
    data = normalize_intent_events(dict(intent))
    ops = event_ops(data)
    if IntentOp.READ.value in ops:
        return IntentOp.READ.value
    for preferred in (
        "end",
        IntentOp.CREATE.value,
        IntentOp.UPDATE.value,
        IntentOp.DELETE.value,
    ):
        if preferred in ops:
            return preferred if preferred != "end" else IntentOp.CREATE.value
    return ""


def _is_timer_leaf(leaf: Dict[str, Any]) -> bool:
    """是否为计时事件：只认字典 event_type=time。"""
    return str(leaf.get("event_type") or "").strip().lower() == "time"


def sort_end_items_first(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """同一 batch 先提交 end，再提交其余项。"""
    ends = [it for it in items if (it.get("op") or "") == "end"]
    rest = [it for it in items if (it.get("op") or "") != "end"]
    return ends + rest


def collect_event_items(
    intent: Dict[str, Any],
    full_events: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    从意图结果收集可落库子项；字典外名称进 missing。

    仅处理 create/update/delete/end；read 不进 batch。
    """
    missing: List[str] = []
    items: List[Dict[str, Any]] = []
    data = normalize_intent_events(dict(intent), full_events)
    raw_events = [e for e in (data.get("events") or []) if isinstance(e, dict)]
    now = int(time.time())
    for ev in raw_events:
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
        item_op = derive_item_op(ev, leaf=leaf)
        if item_op == IntentOp.READ.value:
            continue
        if item_op not in CUD_OPS:
            continue
        action = str(ev.get("action") or "").strip().lower()
        if not action:
            if item_op == "end":
                action = IntentAction.END.value
            elif item_op == IntentOp.CREATE.value:
                action = (
                    IntentAction.START.value
                    if _is_timer_leaf(leaf)
                    else IntentAction.ONE.value
                )
        is_timer = _is_timer_leaf(leaf)
        if item_op == "end" and not is_timer:
            item_op = IntentOp.CREATE.value
            action = IntentAction.ONE.value
        qty = ev.get("quantity")
        if qty is None:
            qty = data.get("quantity")
        try:
            number = int(qty) if qty is not None else 0
        except (TypeError, ValueError):
            number = 0
        start_time = int(ev.get("start_time") or now)
        if item_op == "end":
            hid_int = 0
            end_time = 0
        elif item_op == IntentOp.CREATE.value:
            hid_int = 0
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
                "op": item_op if item_op != IntentOp.CREATE.value else "create",
                "action": action,
                "id": hid_int,
                "eventId": int(str(leaf.get("event_id") or eid) or 0),
                "eventName": leaf.get("event_name") or name,
                "eventUnit": leaf.get("event_unit") or ev.get("event_unit") or "",
                "eventNumber": number,
                "startTime": start_time,
                "endTime": end_time,
                "remark": str(ev.get("remark") or data.get("remark") or ""),
                "_display_name": leaf.get("event_name") or name,
                "_item_op": item_op,
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
    """模板回执：全成功 / 部分成功 / 全失败。"""
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
    """把本轮成功意图改写成可缓存的独立句。"""
    data = normalize_intent_events(dict(intent))
    names = []
    for ev in data.get("events") or []:
        n = (ev.get("event_name") or "").strip()
        if n:
            names.append(n)
    if not names and data.get("event_name"):
        names.append(str(data.get("event_name")))
    ops = event_ops(data)
    remark = (data.get("remark_keyword") or "").strip()
    if not remark:
        for ev in data.get("events") or []:
            if isinstance(ev, dict) and ev.get("remark_keyword"):
                remark = str(ev.get("remark_keyword")).strip()
                break
    joined = "、".join(names) if names else (original or "").strip()
    if IntentOp.READ.value in ops:
        if remark:
            return f"上一次{joined}备注{remark}是什么时候"
        return f"上一次{joined}是什么时候"
    if IntentOp.UPDATE.value in ops:
        return f"把{joined}改一下"
    if IntentOp.DELETE.value in ops:
        return f"删除刚才的{joined}"
    src = (original or "").strip()
    if src and src not in {"嗯", "是的", "好的", "1"}:
        return src
    return f"记录{joined}" if joined else src

"""
预测问答播报节点

业务说明：
target_type=predict 时按 predict_channel 拉 Go active-eta / imminent，
按 time_answer 播报 clock 或 remain；无数据估不准，禁止回落查史用时。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.feeding.schemas.intent_result import IntentResult, coerce_intent_result
from app.feeding.services.predict_qa import (
    format_predict_answer,
    match_active_expect_end,
    match_imminent_next_at,
    uncertainty_message,
)
from app.shared.constants import TargetType
from app.shared.graphs.state_patch import state_get
from app.shared.http_client import http_client

logger = logging.getLogger(__name__)


def _first_event_ids(intent: Dict[str, Any]) -> List[Dict[str, str]]:
    """收集待匹配的事件 id/name（优先 events[]，回落顶层）。"""
    out: List[Dict[str, str]] = []
    for e in intent.get("events") or []:
        if not isinstance(e, dict):
            continue
        eid = str(e.get("event_id") or "").strip()
        if not eid:
            continue
        out.append(
            {
                "event_id": eid,
                "event_name": str(e.get("event_name") or "").strip(),
            }
        )
    if out:
        return out
    eid = str(intent.get("event_id") or "").strip()
    if eid:
        return [
            {
                "event_id": eid,
                "event_name": str(intent.get("event_name") or "").strip(),
            }
        ]
    for raw in intent.get("event_ids") or []:
        s = str(raw or "").strip()
        if s:
            out.append({"event_id": s, "event_name": ""})
    return out


async def speak_predict(state: Any) -> Dict[str, Any]:
    """
    双通道预测播报：active→active-eta；next→imminent pending。

    失败/无匹配：估不准中文；MUST NOT 念「上一次…用时」。
    """
    intent = coerce_intent_result(state_get(state, "intent_result")).to_plain_dict()
    if str(intent.get("target_type") or "").lower() != TargetType.PREDICT.value:
        return {}

    channel = str(intent.get("predict_channel") or "").strip().lower()
    time_answer = str(intent.get("time_answer") or "").strip().lower()
    device_no = state_get(state, "device_no") or ""
    full_events = (
        state_get(state, "event_dictionary_full")
        or state_get(state, "event_dictionary")
        or []
    )
    items = _first_event_ids(intent)
    if (
        channel not in ("active", "next")
        or time_answer not in ("clock", "remain")
        or not items
    ):
        name = items[0]["event_name"] if items else ""
        content = uncertainty_message(name)
        intent["content"] = content
        return {
            "intent_result": IntentResult.model_validate(intent),
            "response": content,
        }

    head = items[0]
    eid = head["event_id"]
    ename = head["event_name"]
    # 名字缺失时从目录补
    if not ename:
        for ev in full_events:
            if str(ev.get("event_id") or "") == eid:
                ename = str(ev.get("event_name") or "").strip()
                break

    anchor: Optional[int] = None
    try:
        if channel == "active":
            eta_items = await http_client.get_predict_active_eta(device_no)
            anchor = match_active_expect_end(eid, eta_items, full_events)
        else:
            pending = await http_client.get_predict_imminent_pending(device_no)
            anchor = match_imminent_next_at(eid, pending, full_events)
    except Exception as exc:
        logger.warning(
            "预测拉数失败，估不准: channel=%s device_no=%s err=%s",
            channel,
            device_no,
            exc,
        )
        anchor = None

    if anchor is None:
        content = uncertainty_message(ename)
    else:
        content = format_predict_answer(
            anchor_unix=anchor,
            time_answer=time_answer,
            predict_channel=channel,
            event_name=ename,
        )

    # 防御：降级文案不得带查史完成句特征
    if "上一次" in content and "用时" in content:
        logger.error("预测播报误含查史用时，强制估不准")
        content = uncertainty_message(ename)

    intent["content"] = content
    return {
        "intent_result": IntentResult.model_validate(intent),
        "response": content,
    }

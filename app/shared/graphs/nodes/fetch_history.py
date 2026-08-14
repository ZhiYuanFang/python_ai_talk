"""
历史拉取节点

业务说明：
根据 data_requirement 拉取历史；支持 Pydantic State / DataRequirement。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Mapping

import httpx

from app.shared.graphs.history_gate import should_fetch_history
from app.shared.graphs.state_patch import state_get
from app.shared.http_client import http_client
from app.shared.schemas.data_requirement import DataRequirement

logger = logging.getLogger(__name__)


def _requirement_mapping(data_requirement: Any) -> Dict[str, Any]:
    """DataRequirement 或 dict → filter 用字典。"""
    if data_requirement is None:
        return {}
    if isinstance(data_requirement, DataRequirement):
        return data_requirement.as_window_dict()
    if isinstance(data_requirement, Mapping):
        return dict(data_requirement)
    return {}


async def fetch_history(state: Any) -> Dict[str, Any]:
    """历史拉取节点：门禁后按 data_requirement filter 或全量。"""
    if not should_fetch_history(state):
        return {"history_events": []}

    device_no = state_get(state, "device_no", "") or ""
    data_requirement = state_get(state, "data_requirement")

    if data_requirement:
        try:
            history_events = await _fetch_with_filter(device_no, data_requirement)
            return {"history_events": history_events}
        except Exception as e:
            logger.warning(f"filter API 失败，降级到全量 API: {str(e)}")
            return await _fetch_all(device_no)
    return await _fetch_all(device_no)


async def _fetch_with_filter(device_no: str, data_requirement: Any) -> list:
    """按 DataRequirement / dict 调 filter。"""
    req = _requirement_mapping(data_requirement)
    event_ids = req.get("event_ids", []) or []
    limit = req.get("limit", 20)
    remark = req.get("remark") or req.get("remark_keyword")

    from app.shared.history_window import resolve_window

    start_time, end_time = resolve_window(req)

    return await http_client.get_filtered_history_events(
        device_no=device_no,
        event_ids=event_ids if event_ids else None,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        remark=str(remark).strip() if remark else None,
    )


async def _fetch_all(device_no: str) -> Dict[str, Any]:
    """全量历史降级。"""
    try:
        history_events = await http_client.get_history_events(
            device_no=device_no,
            limit=100,
        )
        return {"history_events": history_events}
    except Exception as e:
        logger.error(f"全量历史 API 也失败: {str(e)}")
        return {"history_events": []}

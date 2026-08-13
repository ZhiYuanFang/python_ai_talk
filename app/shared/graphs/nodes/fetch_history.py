"""
历史拉取节点

业务说明：
LangGraph 节点：根据 data_requirement 拉取历史记录。
有数据需求判断结果时调用 filter API（按事件ID+时间范围筛选），
没有数据需求时调用全量 API（兼容旧逻辑）。
filter API 不可用时自动降级到全量 API。
若门禁判定不需要历史（且未 force），防御性返回空列表。

设计思路：
1. should_fetch_history 为假则直接返回 []
2. 从 State 中读取 device_no、data_requirement
3. 如果有 data_requirement，调用 get_filtered_history_events
4. 如果没有 data_requirement，调用 get_history_events（全量）
5. filter API 失败时降级到全量 API
6. 返回 history_events 更新 State
"""

import logging
from typing import Any, Dict

import httpx

from app.shared.graphs.history_gate import should_fetch_history
from app.shared.http_client import http_client

# 初始化日志记录器
logger = logging.getLogger(__name__)


async def fetch_history(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    历史拉取节点函数

    业务逻辑：
    1. 门禁防御：needs_history 为 false 且未 force 时直接返回空列表、不打 API
    2. 从 State 中读取设备编号和数据需求
    3. 如果有 data_requirement，计算时间范围并调用 filter API
    4. 如果没有 data_requirement，调用全量 API
    5. filter API 失败时降级到全量 API
    6. 返回 history_events 更新 State

    Args:
        state: 当前图状态

    Returns:
        需要更新的 State 字段字典
    """
    # 主路径应已跳过本节点；此处防御误入
    if not should_fetch_history(state):
        return {"history_events": []}

    # 读取输入参数
    device_no = state.get("device_no", "")
    data_requirement = state.get("data_requirement")

    # 如果有数据需求，使用 filter API
    if data_requirement:
        try:
            history_events = await _fetch_with_filter(device_no, data_requirement)
            return {"history_events": history_events}
        except Exception as e:
            # filter API 失败，降级到全量 API
            logger.warning(f"filter API 失败，降级到全量 API: {str(e)}")
            return await _fetch_all(device_no)
    else:
        # 没有数据需求，直接拉全量（兼容旧逻辑）
        return await _fetch_all(device_no)


async def _fetch_with_filter(
    device_no: str,
    data_requirement: Dict[str, Any],
) -> list:
    """
    使用 filter API 按条件拉取历史记录

    业务逻辑：
    根据 data_requirement 中的 event_ids、time_range、limit，
    计算具体的 startTime 和 endTime，调用 filter API。

    Args:
        device_no: 设备编号
        data_requirement: 数据需求字典

    Returns:
        历史记录列表

    Raises:
        httpx.HTTPError: HTTP 请求失败
    """
    event_ids = data_requirement.get("event_ids", [])
    limit = data_requirement.get("limit", 20)
    remark = data_requirement.get("remark") or data_requirement.get("remark_keyword")

    # 优先用调用方已算好的 unix；仅当缺省时才把遗留枚举换成 unix
    from app.shared.history_window import resolve_window

    start_time, end_time = resolve_window(data_requirement)

    # 调用 filter API（可带备注模糊）
    history_events = await http_client.get_filtered_history_events(
        device_no=device_no,
        event_ids=event_ids if event_ids else None,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        remark=str(remark).strip() if remark else None,
    )

    return history_events


async def _fetch_all(device_no: str) -> Dict[str, Any]:
    """
    拉取全量历史记录（降级方案）

    业务逻辑：
    当 filter API 不可用或没有 data_requirement 时，
    调用全量历史记录 API，返回最近的 100 条记录。

    Args:
        device_no: 设备编号

    Returns:
        需要更新的 State 字段字典
    """
    try:
        history_events = await http_client.get_history_events(
            device_no=device_no,
            limit=100,
        )
        return {"history_events": history_events}
    except Exception as e:
        # 全量 API 也失败了，返回空列表，不中断流程
        logger.error(f"全量历史 API 也失败: {str(e)}")
        return {"history_events": []}

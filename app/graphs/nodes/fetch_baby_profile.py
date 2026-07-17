"""
宝宝画像获取节点

业务说明：
LangGraph 节点：调用设备服务获取宝宝画像信息。
宝宝画像不存在或API失败时返回空字典，不中断图的执行流程。

设计思路：
1. 从 State 中读取 device_no
2. 调用 http_client.get_baby_profile 获取宝宝画像
3. 返回 None 或异常时返回空字典
4. 返回 baby_profile 更新 State
"""

import logging
from typing import Any, Dict

from app.services.http_client import http_client

# 初始化日志记录器
logger = logging.getLogger(__name__)


async def fetch_baby_profile(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    宝宝画像获取节点函数

    业务逻辑：
    1. 从 State 中读取设备编号
    2. 调用设备服务获取宝宝画像
    3. 宝宝画像不存在或API失败时返回空字典
    4. 返回 baby_profile 更新 State

    Args:
        state: 当前图状态

    Returns:
        需要更新的 State 字段字典
    """
    # 读取设备编号
    device_no = state.get("device_no", "")

    if not device_no:
        # 没有设备编号，返回空字典
        return {"baby_profile": {}}

    try:
        # 调用设备服务获取宝宝画像
        profile = await http_client.get_baby_profile(device_no)

        if profile is None:
            # 宝宝画像不存在，返回空字典
            logger.warning(f"宝宝画像不存在: device_no={device_no}")
            return {"baby_profile": {}}

        return {"baby_profile": profile}

    except Exception as e:
        # API 调用失败，返回空字典，不中断流程
        logger.error(f"获取宝宝画像失败: device_no={device_no}, error={str(e)}")
        return {"baby_profile": {}}

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

from app.shared.graphs.state_patch import state_get

from app.shared.graphs.state_patch import state_get
from app.shared.http_client import http_client

# 初始化日志记录器
logger = logging.getLogger(__name__)


async def fetch_baby_profile(state: Any) -> Dict[str, Any]:
    """宝宝画像获取节点。"""
    device_no = state_get(state, "device_no", "") or ""

    if not device_no:
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

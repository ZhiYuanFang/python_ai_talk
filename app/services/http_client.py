"""
HTTP 客户端模块

业务说明：
本模块负责封装对 go_ai_talk 兄弟仓服务的 HTTP 调用。
包括历史服务（history-service）和设备服务（device-service）。

设计思路：
1. 使用 httpx 作为异步 HTTP 客户端
2. 封装常用的 API 调用方法
3. 统一错误处理和日志记录
4. 支持超时配置和重试机制
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from app.config.settings import settings

# 初始化日志记录器
logger = logging.getLogger(__name__)


class HttpClient:
    """
    HTTP 客户端类

    业务说明：
    提供对 go_ai_talk 兄弟仓服务的 HTTP 调用能力。
    封装历史服务和设备服务的常用 API。
    """

    def __init__(self):
        """
        初始化 HTTP 客户端

        业务逻辑：
        1. 创建 httpx.AsyncClient 实例
        2. 配置超时时间和连接池
        """
        # 创建 httpx 异步客户端
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),  # 请求超时时间
            limits=httpx.Limits(
                max_connections=10,  # 最大连接数
                max_keepalive_connections=5,  # 最大长连接数
            ),
            follow_redirects=True,  # 自动跟随重定向
        )

    async def get_event_dictionary(self) -> List[Dict[str, Any]]:
        """
        获取事件字典列表

        业务逻辑：
        调用 history-service 的事件字典 API，获取所有可用的事件类型。
        用于意图分析时匹配事件名称。

        Returns:
            事件字典列表，格式为 [{"event_name": "...", "keywords": [...]}, ...]

        Raises:
            httpx.HTTPError: HTTP 请求失败
        """
        # 构建请求 URL
        url = f"{settings.history_service_url}/api/events/dictionary"

        try:
            # 发起 GET 请求
            response = await self._client.get(url)

            # 检查响应状态码
            response.raise_for_status()

            # 返回解析后的 JSON 数据
            return response.json()

        except httpx.HTTPError as e:
            # 记录错误日志
            logger.error(f"获取事件字典失败: {str(e)}")
            raise

    async def get_history_events(
        self,
        device_no: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取历史事件列表

        业务逻辑：
        调用 history-service 的历史记录 API，获取指定设备的历史事件。
        支持时间范围和数量限制。

        Args:
            device_no: 设备编号
            start_time: 开始时间戳（可选）
            end_time: 结束时间戳（可选）
            limit: 返回数量限制（可选）

        Returns:
            历史事件列表

        Raises:
            httpx.HTTPError: HTTP 请求失败
        """
        # 构建请求 URL
        url = f"{settings.history_service_url}/api/events/list"

        # 构建查询参数
        params: Dict[str, Any] = {
            "deviceNo": device_no,
        }

        # 添加可选参数
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time
        if limit is not None:
            params["limit"] = limit

        try:
            # 发起 GET 请求
            response = await self._client.get(url, params=params)

            # 检查响应状态码
            response.raise_for_status()

            # 返回解析后的 JSON 数据
            return response.json()

        except httpx.HTTPError as e:
            # 记录错误日志
            logger.error(f"获取历史事件失败: device_no={device_no}, error={str(e)}")
            raise

    async def get_filtered_history_events(
        self,
        device_no: str,
        event_ids: Optional[List[int]] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        按条件筛选历史记录

        业务逻辑：
        调用 history-service 的筛选 API，按事件ID列表和时间范围筛选历史记录。
        事件ID是稳定标识（事件名会变但ID不变），因此使用 event_ids 而非 event_names。
        支持不传 event_ids（返回所有事件类型）、不传时间范围（不限制时间）。

        Args:
            device_no: 设备编号
            event_ids: 事件ID列表，为空表示所有事件类型
            start_time: 开始时间戳（Unix秒，可选）
            end_time: 结束时间戳（Unix秒，可选）
            limit: 返回数量上限（可选，默认100）

        Returns:
            筛选后的历史事件列表

        Raises:
            httpx.HTTPError: HTTP 请求失败
        """
        # 构建请求 URL
        url = f"{settings.history_service_url}/device/history/api/filter"

        # 构建查询参数
        params: Dict[str, Any] = {
            "deviceNo": device_no,
        }

        # 添加事件ID参数（逗号分隔字符串）
        if event_ids and len(event_ids) > 0:
            params["eventIds"] = ",".join(str(eid) for eid in event_ids)

        # 添加时间范围参数
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time

        # 添加数量限制
        if limit is not None:
            params["limit"] = limit

        try:
            # 发起 GET 请求
            response = await self._client.get(url, params=params)

            # 检查响应状态码
            response.raise_for_status()

            # 返回解析后的 JSON 数据（list 字段）
            data = response.json()
            return data.get("list", [])

        except httpx.HTTPError as e:
            # 记录错误日志
            logger.error(
                f"筛选历史记录失败: device_no={device_no}, "
                f"event_ids={event_ids}, error={str(e)}"
            )
            raise

    async def get_baby_profile(self, device_no: str) -> Optional[Dict[str, Any]]:
        """
        获取宝宝画像信息

        业务逻辑：
        调用 device-service 的宝宝画像 API，获取指定设备对应的宝宝信息。
        主要用于获取宝宝生日，计算宝宝年龄。

        Args:
            device_no: 设备编号

        Returns:
            宝宝画像信息，包含生日等字段；如果不存在返回 None

        Raises:
            httpx.HTTPError: HTTP 请求失败
        """
        # 构建请求 URL
        url = f"{settings.device_service_url}/api/device/{device_no}/baby"

        try:
            # 发起 GET 请求
            response = await self._client.get(url)

            # 检查响应状态码
            if response.status_code == 404:
                # 设备不存在或没有宝宝信息，返回 None
                logger.warning(f"宝宝画像不存在: device_no={device_no}")
                return None

            response.raise_for_status()

            # 返回解析后的 JSON 数据
            return response.json()

        except httpx.HTTPError as e:
            # 记录错误日志
            logger.error(f"获取宝宝画像失败: device_no={device_no}, error={str(e)}")
            raise

    async def close(self):
        """
        关闭 HTTP 客户端

        业务逻辑：
        关闭 httpx 客户端连接，释放资源
        """
        await self._client.aclose()


# 创建全局 HTTP 客户端实例
http_client = HttpClient()
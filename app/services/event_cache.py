"""
事件字典缓存模块

业务说明：
本模块负责缓存从兄弟仓获取的事件字典列表，避免频繁调用兄弟仓 API。
缓存 TTL 为 24 小时，过期后自动重新获取。

设计思路：
1. 使用 cachetools.TTLCache 实现简单的内存缓存
2. 提供获取事件字典的方法，自动处理缓存命中和失效逻辑
3. 支持手动刷新缓存
4. 线程安全，支持并发访问
"""

import logging
import threading
from typing import Any, Dict, List, Optional

from cachetools import TTLCache

from app.config.settings import settings
from app.services.http_client import http_client

# 初始化日志记录器
logger = logging.getLogger(__name__)


class EventCache:
    """
    事件字典缓存类

    业务说明：
    缓存从 history-service 获取的事件字典列表，用于意图分析时匹配事件名称。
    缓存有效期为 24 小时，过期后自动重新获取。
    """

    def __init__(self):
        """
        初始化事件字典缓存

        业务逻辑：
        1. 创建 TTLCache 实例，设置 TTL 为 24 小时
        2. 初始化线程锁，确保线程安全
        """
        # 创建 TTLCache 实例
        # maxsize: 最大缓存数量（这里只缓存一个事件字典列表）
        # ttl: 缓存有效期（秒），24小时 = 86400 秒
        self._cache = TTLCache(
            maxsize=1,
            ttl=settings.event_cache_ttl_hours * 3600,
        )

        # 创建线程锁，确保线程安全
        # 在多线程环境下，防止多个线程同时获取事件字典
        self._lock = threading.Lock()

        # 缓存 key
        self._CACHE_KEY = "event_dictionary"

    async def get_event_dictionary(self) -> List[Dict[str, Any]]:
        """
        获取事件字典列表

        业务逻辑：
        1. 检查缓存是否命中
        2. 如果命中，直接返回缓存的数据
        3. 如果未命中，从兄弟仓获取数据并缓存
        4. 使用线程锁确保线程安全

        Returns:
            事件字典列表
        """
        # 检查缓存是否命中
        if self._CACHE_KEY in self._cache:
            # 缓存命中，直接返回
            logger.debug("事件字典缓存命中")
            return self._cache[self._CACHE_KEY]

        # 缓存未命中，获取线程锁
        # 防止多个线程同时从兄弟仓获取数据
        with self._lock:
            # 再次检查缓存（双重检查锁定）
            # 因为在获取锁的过程中，可能已经有其他线程更新了缓存
            if self._CACHE_KEY in self._cache:
                logger.debug("事件字典缓存命中（双重检查）")
                return self._cache[self._CACHE_KEY]

            # 从兄弟仓获取事件字典
            logger.info("事件字典缓存未命中，从兄弟仓获取...")
            event_dictionary = await http_client.get_event_dictionary()

            # 将数据存入缓存
            self._cache[self._CACHE_KEY] = event_dictionary

            # 记录获取成功日志
            logger.info(f"成功获取并缓存事件字典，包含 {len(event_dictionary)} 个事件")

            return event_dictionary

    async def refresh(self):
        """
        手动刷新缓存

        业务逻辑：
        1. 清除现有缓存
        2. 重新从兄弟仓获取事件字典
        3. 更新缓存
        """
        logger.info("手动刷新事件字典缓存...")

        # 获取线程锁
        with self._lock:
            # 从兄弟仓获取事件字典
            event_dictionary = await http_client.get_event_dictionary()

            # 更新缓存
            self._cache[self._CACHE_KEY] = event_dictionary

            # 记录刷新成功日志
            logger.info(f"事件字典缓存刷新成功，包含 {len(event_dictionary)} 个事件")

    def is_expired(self) -> bool:
        """
        检查缓存是否已过期

        业务逻辑：
        检查缓存 key 是否存在，如果不存在说明已过期或从未缓存

        Returns:
            True 表示已过期，False 表示未过期
        """
        return self._CACHE_KEY not in self._cache

    def get_cache_info(self) -> Dict[str, Any]:
        """
        获取缓存状态信息

        业务逻辑：
        返回缓存的统计信息，用于监控和调试

        Returns:
            缓存状态信息，包含 hits（命中次数）、misses（未命中次数）、maxsize（最大缓存数）、currsize（当前缓存数）
        """
        info = self._cache.cache_info()
        return {
            "hits": info.hits,
            "misses": info.misses,
            "maxsize": info.maxsize,
            "currsize": info.currsize,
        }


# 创建全局事件字典缓存实例
event_cache = EventCache()
"""
事件字典缓存模块

业务说明：
本模块负责缓存从兄弟仓获取的事件字典列表，避免频繁调用兄弟仓 API。
缓存 TTL 为 24 小时，过期后自动重新获取。
新增：缓存更新时自动同步喂养事件向量库。

设计思路：
1. 使用 cachetools.TTLCache 实现简单的内存缓存
2. 提供获取事件字典的方法，自动处理缓存命中和失效逻辑
3. 支持手动刷新缓存
4. 线程安全，支持并发访问
5. 缓存更新时检测变化并同步喂养事件向量库
"""

import logging
import threading
from typing import Any, Dict, List, Optional

from cachetools import TTLCache

from app.config.settings import settings
from app.shared.http_client import http_client

# 初始化日志记录器
logger = logging.getLogger(__name__)


class EventCache:
    """
    事件字典缓存类

    业务说明：
    缓存从 history-service 获取的事件字典列表，用于意图分析时匹配事件名称。
    缓存有效期为 24 小时，过期后自动重新获取。
    缓存更新时自动检测变化并同步喂养事件向量库。
    采用延迟初始化模式，import 阶段不创建缓存对象，第一次调用时才初始化。
    """

    def __init__(self):
        """
        初始化事件字典缓存（轻量初始化，延迟创建缓存）

        业务逻辑：
        1. 仅设置初始化标记和线程锁，不创建 TTLCache
        2. 实际初始化在第一次调用公共方法时通过 _ensure_initialized() 执行
        3. 延迟初始化的目的：避免 import 阶段分配资源，提升服务启动健壮性
        """
        # 初始化标记（False 表示尚未初始化）
        self._initialized = False

        # 线程锁，确保并发安全的延迟初始化
        import threading
        self._init_lock = threading.Lock()

    def _ensure_initialized(self):
        """
        确保事件字典缓存已初始化（延迟创建）

        业务逻辑：
        第一次调用时创建 TTLCache 实例和相关属性。
        使用双重检查锁定确保并发安全。
        """
        # 第一次检查：无锁快速路径
        if self._initialized:
            return

        # 获取锁
        with self._init_lock:
            # 第二次检查：确保只有一个线程执行初始化
            if not self._initialized:
                # 创建 TTLCache 实例
                # maxsize: 最大缓存数量（这里只缓存一个事件字典列表）
                # ttl: 缓存有效期（秒），24小时 = 86400 秒
                self._cache = TTLCache(
                    maxsize=1,
                    ttl=settings.event_cache_ttl_hours * 3600,
                )

                # 缓存 key
                self._CACHE_KEY = "event_dictionary"

                # 记录上一次获取的事件字典，用于变化检测
                # 当缓存过期重新获取时，比较新旧数据，同步更新向量库
                self._previous_dictionary: Optional[List[Dict[str, Any]]] = None

                # 缓存操作线程锁，确保线程安全
                # 在多线程环境下，防止多个线程同时获取事件字典
                self._cache_lock = threading.Lock()

                # 标记初始化完成
                self._initialized = True

    async def get_event_dictionary(self) -> List[Dict[str, Any]]:
        """
        获取事件字典列表

        业务逻辑：
        1. 确保缓存已初始化（延迟创建）
        2. 检查缓存是否命中
        3. 如果命中，直接返回缓存的数据
        4. 如果未命中，从兄弟仓获取数据并缓存
        5. 缓存更新时检测变化并同步向量库
        6. 使用线程锁确保线程安全

        Returns:
            事件字典列表
        """
        # 确保缓存已初始化（延迟创建）
        self._ensure_initialized()

        # 检查缓存是否命中
        if self._CACHE_KEY in self._cache:
            # 缓存命中，直接返回
            logger.debug("事件字典缓存命中")
            return self._cache[self._CACHE_KEY]

        # 缓存未命中，获取线程锁
        # 防止多个线程同时从兄弟仓获取数据
        with self._cache_lock:
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

            # 检测事件字典变化并同步向量库
            await self._sync_vector_store_if_changed(event_dictionary)

            return event_dictionary

    async def _sync_vector_store_if_changed(self, new_dictionary: List[Dict[str, Any]]):
        """
        检测事件字典变化并同步向量库

        业务逻辑：
        1. 如果是首次获取（无上一次数据），初始化向量库
        2. 否则比较新旧数据，检测新增、修改、删除的事件
        3. 调用向量库同步方法更新数据

        Args:
            new_dictionary: 新获取的事件字典列表
        """
        # 延迟导入，避免循环依赖
        from app.feeding.services.event_vector_store import event_vector_store

        # 如果是首次获取，初始化向量库
        if self._previous_dictionary is None:
            logger.info("首次获取事件字典，初始化喂养事件向量库...")
            # 初始化向量库（创建标准事件和动作变体）
            event_vector_store.initialize_events(new_dictionary)
            # 记录当前数据为上一次数据
            self._previous_dictionary = new_dictionary
            return

        # 比较新旧数据，检测变化
        old_ids = {e.get("event_id") for e in self._previous_dictionary}
        new_ids = {e.get("event_id") for e in new_dictionary}

        # 找出新增的事件ID
        added_ids = new_ids - old_ids
        # 找出删除的事件ID
        removed_ids = old_ids - new_ids
        # 找出可能修改的事件ID（新旧都有，但内容可能变化）
        common_ids = new_ids & old_ids

        # 构建新增事件列表
        added_events = [e for e in new_dictionary if e.get("event_id") in added_ids]
        # 构建删除事件ID列表
        removed_event_ids = list(removed_ids)

        # 构建修改事件列表（比较名称和父级ID是否变化）
        modified_events = []
        # 创建旧事件的ID到事件的映射，便于快速查找
        old_event_map = {e.get("event_id"): e for e in self._previous_dictionary}
        # 遍历共有的事件ID，检查是否发生变化
        for event_id in common_ids:
            old_event = old_event_map.get(event_id, {})
            new_event = next((e for e in new_dictionary if e.get("event_id") == event_id), {})
            # 比较事件名称和父级ID是否变化
            if (old_event.get("event_name") != new_event.get("event_name") or
                    old_event.get("parent_id") != new_event.get("parent_id")):
                # 内容有变化，加入修改列表
                modified_events.append(new_event)

        # 只有存在变化时才同步向量库
        if added_events or removed_event_ids or modified_events:
            logger.info(
                f"检测到事件字典变化：新增 {len(added_events)} 个，"
                f"删除 {len(removed_event_ids)} 个，"
                f"修改 {len(modified_events)} 个，同步向量库..."
            )
            # 调用向量库同步方法
            event_vector_store.sync_events(
                event_dictionary=new_dictionary,
                added_events=added_events,
                removed_event_ids=removed_event_ids,
                modified_events=modified_events,
            )
        else:
            # 无变化，跳过同步
            logger.debug("事件字典无变化，跳过向量库同步")

        # 更新上一次数据
        self._previous_dictionary = new_dictionary

    async def refresh(self):
        """
        手动刷新缓存

        业务逻辑：
        1. 确保缓存已初始化（延迟创建）
        2. 清除现有缓存
        3. 重新从兄弟仓获取事件字典
        4. 更新缓存
        5. 检测变化并同步向量库
        """
        # 确保缓存已初始化（延迟创建）
        self._ensure_initialized()

        logger.info("手动刷新事件字典缓存...")

        # 获取线程锁
        with self._cache_lock:
            # 从兄弟仓获取事件字典
            event_dictionary = await http_client.get_event_dictionary()

            # 更新缓存
            self._cache[self._CACHE_KEY] = event_dictionary

            # 记录刷新成功日志
            logger.info(f"事件字典缓存刷新成功，包含 {len(event_dictionary)} 个事件")

            # 检测变化并同步向量库
            await self._sync_vector_store_if_changed(event_dictionary)

    def is_expired(self) -> bool:
        """
        检查缓存是否已过期

        业务逻辑：
        1. 确保缓存已初始化（延迟创建）
        2. 检查缓存 key 是否存在，如果不存在说明已过期或从未缓存

        Returns:
            True 表示已过期，False 表示未过期
        """
        # 确保缓存已初始化（延迟创建）
        self._ensure_initialized()

        return self._CACHE_KEY not in self._cache

    def get_cache_info(self) -> Dict[str, Any]:
        """
        获取缓存状态信息

        业务逻辑：
        1. 确保缓存已初始化（延迟创建）
        2. 返回缓存的统计信息，用于监控和调试

        Returns:
            缓存状态信息，包含 hits（命中次数）、misses（未命中次数）、maxsize（最大缓存数）、currsize（当前缓存数）
        """
        # 确保缓存已初始化（延迟创建）
        self._ensure_initialized()

        info = self._cache.cache_info()
        return {
            "hits": info.hits,
            "misses": info.misses,
            "maxsize": info.maxsize,
            "currsize": info.currsize,
        }


# 创建全局事件字典缓存实例
event_cache = EventCache()

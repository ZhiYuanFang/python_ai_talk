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

                # 记录上一次获取的全量事件字典，用于变化检测
                # 当缓存过期重新获取时，比较新旧数据，同步更新向量库
                self._previous_dictionary: Optional[List[Dict[str, Any]]] = None

                # 缓存操作线程锁，确保线程安全
                # 在多线程环境下，防止多个线程同时获取事件字典
                self._cache_lock = threading.Lock()

                # 标记初始化完成
                self._initialized = True

    def _leaf_view(self, full: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """从全量树派生叶子视图（排除有子节点的父事件）。"""
        from app.feeding.services.event_hierarchy import get_leaf_events

        return get_leaf_events(full)

    async def get_full_event_dictionary(self) -> List[Dict[str, Any]]:
        """
        获取全量事件字典（含父事件，供父名检测与消歧）。

        Returns:
            全量事件字典列表
        """
        return await self._get_or_load_full_dictionary()

    async def get_event_dictionary(self) -> List[Dict[str, Any]]:
        """
        获取叶子事件字典列表（供匹配候选与落库）。

        业务逻辑：
        1. 确保缓存已初始化（延迟创建）
        2. 获取全量字典（缓存命中或兄弟仓拉取）
        3. 派生并返回叶子视图

        Returns:
            叶子事件字典列表
        """
        full = await self._get_or_load_full_dictionary()
        return self._leaf_view(full)

    async def _get_or_load_full_dictionary(self) -> List[Dict[str, Any]]:
        """获取或加载全量事件字典（24h TTL）。"""
        # 确保缓存已初始化（延迟创建）
        self._ensure_initialized()

        # 检查缓存是否命中
        if self._CACHE_KEY in self._cache:
            logger.debug("事件字典缓存命中")
            return self._cache[self._CACHE_KEY]

        # 缓存未命中，获取线程锁
        with self._cache_lock:
            if self._CACHE_KEY in self._cache:
                logger.debug("事件字典缓存命中（双重检查）")
                return self._cache[self._CACHE_KEY]

            # 从兄弟仓获取全量事件字典
            logger.info("事件字典缓存未命中，从兄弟仓获取...")
            event_dictionary = await http_client.get_event_dictionary()

            # 空列表不写入长 TTL，避免一次空结果毒化 24h
            if not event_dictionary:
                logger.warning(
                    "兄弟仓返回事件字典为空，未写入长 TTL 缓存（下次请求将重试拉取）"
                )
                return []

            # 将全量数据存入缓存
            self._cache[self._CACHE_KEY] = event_dictionary

            leaf_count = len(self._leaf_view(event_dictionary))
            logger.info(
                f"成功获取并缓存事件字典，全量 {len(event_dictionary)} 个事件，"
                f"叶子 {leaf_count} 个"
            )

            # 检测事件字典变化并同步向量库（仅同步叶子标准条目）
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
        from app.feeding.services.event_hierarchy import get_leaf_events, is_parent_event
        from app.feeding.services.event_vector_store import event_vector_store

        new_leaves = get_leaf_events(new_dictionary)

        # 如果是首次获取，初始化向量库（仅叶子）
        if self._previous_dictionary is None:
            logger.info("首次获取事件字典，初始化喂养事件向量库（仅叶子）...")
            event_vector_store.initialize_events(new_leaves)
            self._previous_dictionary = new_dictionary
            return

        old_leaves = get_leaf_events(self._previous_dictionary)

        # 比较新旧叶子，检测变化（ID 统一为 str）
        old_ids = {
            str(eid)
            for e in old_leaves
            if (eid := e.get("event_id")) is not None and eid != ""
        }
        new_ids = {
            str(eid)
            for e in new_leaves
            if (eid := e.get("event_id")) is not None and eid != ""
        }

        # 父事件若曾作为标准条目存在，也加入删除集
        old_full_ids = {
            str(eid)
            for e in self._previous_dictionary
            if (eid := e.get("event_id")) is not None and eid != ""
        }
        parent_ids_to_remove = [
            eid
            for eid in old_full_ids
            if is_parent_event(eid, new_dictionary) or (
                eid not in new_ids and is_parent_event(eid, self._previous_dictionary)
            )
        ]

        added_ids = new_ids - old_ids
        removed_ids = old_ids - new_ids
        common_ids = new_ids & old_ids

        added_events = [
            e for e in new_leaves
            if e.get("event_id") is not None
            and e.get("event_id") != ""
            and str(e.get("event_id")) in added_ids
        ]
        # 叶子删除走完整删除；父事件仅移除标准条目以保留飞轮
        removed_event_ids = list(removed_ids)

        for pid in parent_ids_to_remove:
            event_vector_store.remove_standard_entries_for_event(pid)
            logger.info(f"移除父事件标准向量: event_id={pid}")

        modified_events = []
        old_event_map = {
            str(eid): e
            for e in old_leaves
            if (eid := e.get("event_id")) is not None and eid != ""
        }
        for event_id in common_ids:
            old_event = old_event_map.get(event_id, {})
            new_event = next(
                (
                    e for e in new_leaves
                    if e.get("event_id") is not None
                    and str(e.get("event_id")) == event_id
                ),
                {},
            )
            old_parent = old_event.get("parent_id")
            new_parent = new_event.get("parent_id")
            old_parent_s = "" if old_parent is None else str(old_parent)
            new_parent_s = "" if new_parent is None else str(new_parent)
            if (
                old_event.get("event_name") != new_event.get("event_name")
                or old_parent_s != new_parent_s
            ):
                modified_events.append(new_event)

        if added_events or removed_event_ids or modified_events:
            logger.info(
                f"检测到事件字典变化：新增 {len(added_events)} 个叶子，"
                f"删除 {len(removed_event_ids)} 个，"
                f"修改 {len(modified_events)} 个，同步向量库..."
            )
            event_vector_store.sync_events(
                event_dictionary=new_leaves,
                added_events=added_events,
                removed_event_ids=removed_event_ids,
                modified_events=modified_events,
            )
        else:
            logger.debug("事件字典叶子视图无变化，跳过向量库同步")

        self._previous_dictionary = new_dictionary

    async def refresh(self):
        """
        手动刷新缓存

        业务逻辑：
        1. 确保缓存已初始化（延迟创建）
        2. 清除现有缓存
        3. 重新从兄弟仓获取全量事件字典
        4. 更新缓存
        5. 检测变化并同步向量库（仅叶子）
        """
        # 确保缓存已初始化（延迟创建）
        self._ensure_initialized()

        logger.info("手动刷新事件字典缓存...")

        # 获取线程锁
        with self._cache_lock:
            # 从兄弟仓获取全量事件字典
            event_dictionary = await http_client.get_event_dictionary()

            # 空列表不写入长 TTL（与 get 路径一致，避免毒化）
            if not event_dictionary:
                # 清除旧缓存，强制下次重新拉取
                self._cache.pop(self._CACHE_KEY, None)
                logger.warning(
                    "手动刷新时兄弟仓返回事件字典为空，未写入长 TTL 缓存"
                )
                return

            # 更新全量缓存
            self._cache[self._CACHE_KEY] = event_dictionary

            leaf_count = len(self._leaf_view(event_dictionary))
            logger.info(
                f"事件字典缓存刷新成功，全量 {len(event_dictionary)} 个事件，"
                f"叶子 {leaf_count} 个"
            )

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

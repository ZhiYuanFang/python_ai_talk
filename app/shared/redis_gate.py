"""
Redis 闸门控制模块

业务说明：
本模块实现基于 Redis 的并发控制机制，用于限制 LLM 调用的并发数。
与 Go 项目中的闸门控制逻辑保持一致，使用相同的 Redis Key 格式。

设计思路：
1. 使用 Redis 的 INCR/DECR 命令实现原子计数器
2. 使用 Lua 脚本确保计数器操作的原子性
3. Key 格式与 Go 项目保持一致：llm_gate:{model}:inflight
4. 支持异步上下文管理器模式，自动释放许可
"""

import asyncio
import logging
from contextlib import asynccontextmanager
import redis
from redis.cluster import RedisCluster
import redis.asyncio as redis

from app.config.settings import settings

# 初始化日志记录器
logger = logging.getLogger(__name__)


class RedisGate:
    """
    Redis 闸门控制器

    业务说明：
    用于限制 LLM 调用的并发数，避免超过 API 提供商的限制。
    使用 Redis 作为分布式计数器，支持多实例部署。
    """

    def __init__(self):
        """
        初始化 Redis 闸门控制器

        业务逻辑：
        1. 创建 Redis 连接客户端
        2. 定义 Lua 脚本用于原子性操作
        """
        # 创建 Redis 连接客户端
        # 判断是否是集群模式
        if "," in settings.redis_url:  # 包含逗号说明是多节点集群
            self._redis = RedisCluster.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
        else:
            self._redis = redis.Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )

        # Lua 脚本：尝试获取许可
        # 如果当前并发数 < max_in_flight，则增加计数器并返回 1（成功）
        # 否则返回 0（失败）
        self._acquire_script = """
            local key = KEYS[1]
            local max_in_flight = tonumber(ARGV[1])
            local current = tonumber(redis.call('GET', key) or '0')
            if current < max_in_flight then
                redis.call('INCR', key)
                return 1
            else
                return 0
            end
        """

        # Lua 脚本：释放许可
        # 减少计数器，确保不小于 0
        self._release_script = """
            local key = KEYS[1]
            local current = tonumber(redis.call('GET', key) or '0')
            if current > 0 then
                redis.call('DECR', key)
            end
            return 1
        """

    def _get_key(self, model_name: str) -> str:
        """
        生成 Redis Key

        业务逻辑：
        Key 格式与 Go 项目保持一致：llm_gate:{model}:inflight

        Args:
            model_name: 模型名称

        Returns:
            Redis Key 字符串
        """
        return f"llm_gate:{model_name}:inflight"

    @asynccontextmanager
    async def acquire(self, model_name: str, max_in_flight: int = 3, timeout: int = 30):
        """
        获取并发许可（异步上下文管理器模式）

        业务逻辑：
        1. 尝试获取许可，如果当前并发数未达到上限则成功
        2. 如果获取失败，等待一段时间后重试
        3. 如果超时仍未获取到许可，抛出异常
        4. 使用 async with 模式自动释放许可

        Args:
            model_name: 模型名称
            max_in_flight: 最大并发数
            timeout: 超时时间（秒）

        Yields:
            None（进入上下文表示获取成功）

        Raises:
            TimeoutError: 超时未获取到许可
        """
        # 生成 Redis Key
        key = self._get_key(model_name)

        # 计算超时时间点
        deadline = asyncio.get_event_loop().time() + timeout

        try:
            # 循环尝试获取许可
            while asyncio.get_event_loop().time() < deadline:
                # 执行 Lua 脚本获取许可
                result = await self._redis.eval(
                    self._acquire_script,
                    keys=[key],
                    args=[max_in_flight],
                )

                # 如果获取成功，返回上下文
                if result == 1:
                    # 记录获取许可日志
                    current = await self._redis.get(key)
                    logger.debug(f"成功获取 LLM 并发许可: model={model_name}, inflight={current}, max={max_in_flight}")
                    yield
                    return

                # 获取失败，等待后重试
                # 等待时间随重试次数递增，避免过度频繁重试
                await asyncio.sleep(0.1)

            # 超时未获取到许可
            raise TimeoutError(f"获取 LLM 并发许可超时: model={model_name}, max_in_flight={max_in_flight}")

        finally:
            # 释放许可（无论成功还是失败都要释放）
            await self._release_script_exec(key)

    async def _release_script_exec(self, key: str):
        """
        执行释放许可的 Lua 脚本

        业务逻辑：
        减少计数器，确保不小于 0

        Args:
            key: Redis Key
        """
        try:
            await self._redis.eval(
                self._release_script,
                keys=[key],
                args=[],
            )
            # 记录释放许可日志
            current = await self._redis.get(key)
            logger.debug(f"释放 LLM 并发许可: key={key}, inflight={current}")
        except Exception as e:
            # 释放许可失败记录警告日志，但不抛出异常
            logger.warning(f"释放 LLM 并发许可失败: {str(e)}")

    async def get_current_inflight(self, model_name: str) -> int:
        """
        获取当前并发数

        业务逻辑：
        从 Redis 获取当前模型的并发数

        Args:
            model_name: 模型名称

        Returns:
            当前并发数
        """
        key = self._get_key(model_name)
        result = await self._redis.get(key)
        return int(result) if result else 0

    async def close(self):
        """
        关闭 Redis 连接

        业务逻辑：
        关闭 Redis 客户端连接，释放资源
        """
        await self._redis.close()

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
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import redis.asyncio as redis
from redis.asyncio.cluster import ClusterNode, RedisCluster

from app.config.settings import settings

# 初始化日志记录器
logger = logging.getLogger(__name__)


def _parse_node_host_port(node: str) -> Optional[Tuple[str, int]]:
    """
    解析单个集群节点地址为 (host, port)

    业务说明：
    生产 URL 形如 redis://host1:7001,host2:7002,host3:7003
    逗号拆分后，首段带 scheme，后续段常为裸 host:port（无 redis://）。
    redis-py 5.x 要求 startup_nodes 为 ClusterNode，不能传 dict。

    Args:
        node: 单个节点字符串（可含 scheme、密码、/db 后缀）

    Returns:
        (hostname, port)；无法解析时返回 None
    """
    # 去掉首尾空白，避免配置中空格导致解析失败
    node = node.strip()
    if not node:
        return None

    # 带 scheme（或 //host:port）时走 urlparse
    if "://" in node or node.startswith("//"):
        parsed = urlparse(node if "://" in node else f"redis:{node}")
        if parsed.hostname and parsed.port:
            return parsed.hostname, parsed.port
        return None

    # 无 scheme：host:port 或 host:port/db
    hostport = node.split("/", 1)[0]
    if ":" not in hostport:
        return None
    host, port_str = hostport.rsplit(":", 1)
    if not host:
        return None
    try:
        return host, int(port_str)
    except ValueError:
        return None


def _build_cluster_startup_nodes(redis_url: str) -> Tuple[List[ClusterNode], Optional[str]]:
    """
    从逗号分隔的集群 URL 构建 ClusterNode 列表与共享密码

    解析规则：
    1. 按逗号拆分多节点
    2. 密码仅从首段 URL 的 userinfo 读取，供整个集群客户端使用
    3. 每段用 _parse_node_host_port 得到 host/port，包装为 ClusterNode

    Args:
        redis_url: 含逗号的集群 Redis URL

    Returns:
        (startup_nodes, password)
    """
    nodes = redis_url.split(",")
    # 从第一个节点 URL 解析密码（后续裸 host:port 通常不含密码）
    first_parsed = urlparse(nodes[0].strip())
    password = first_parsed.password

    startup_nodes: List[ClusterNode] = []
    for node in nodes:
        host_port = _parse_node_host_port(node)
        if host_port is None:
            logger.warning(f"跳过无法解析的 Redis 集群节点段: {node!r}")
            continue
        host, port = host_port
        # redis-py 5.x：必须传 ClusterNode，dict 会触发 AttributeError: 'dict' has no attribute 'host'
        startup_nodes.append(ClusterNode(host, port))

    return startup_nodes, password


def create_async_redis_client():
    """
    创建与闸门/陪伴会话共用的异步 Redis 客户端。

    业务逻辑：
    1. URL 含逗号 → 集群 RedisCluster + ClusterNode
    2. 否则 → 单机 Redis.from_url
    3. decode_responses=True，便于直接读写 JSON 字符串

    Returns:
        redis.asyncio.Redis 或 RedisCluster 实例
    """
    if "," in settings.redis_url:
        startup_nodes, password = _build_cluster_startup_nodes(settings.redis_url)
        if not startup_nodes:
            raise ValueError(f"Redis 集群 URL 未解析出任何节点: {settings.redis_url!r}")
        return RedisCluster(
            startup_nodes=startup_nodes,
            password=password,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
        )
    return redis.Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
    )


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
        1. 创建 Redis 连接客户端（支持单机和集群模式）
        2. 定义 Lua 脚本用于原子性操作

        集群模式 URL 格式示例：
        redis://host1:7001,host2:7002,host3:7003/0
        （逗号分隔多个节点地址；后续节点可省略 redis://）
        """
        # 与陪伴会话共用同一套客户端构造逻辑
        self._redis = create_async_redis_client()
        self._is_cluster = "," in settings.redis_url

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
                # redis-py 签名为 eval(script, numkeys, *keys_and_args)，不支持 keys=/args= 关键字
                result = await self._redis.eval(
                    self._acquire_script,
                    1,
                    key,
                    max_in_flight,
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
            # redis-py：eval(script, numkeys, *keys_and_args)；本脚本仅 1 个 KEY，无 ARGV
            await self._redis.eval(
                self._release_script,
                1,
                key,
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

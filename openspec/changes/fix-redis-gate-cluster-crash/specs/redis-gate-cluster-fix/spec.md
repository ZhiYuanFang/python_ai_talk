## ADDED Requirements

### Requirement: Redis 集群模式连接支持
Redis 闸门模块 SHALL 支持逗号分隔的多节点 Redis 集群 URL，通过手动解析节点地址并使用 `startup_nodes` 参数创建 `RedisCluster` 客户端。

#### Scenario: 三节点集群 URL 解析成功
- **WHEN** `redis_url` 配置为 `redis://host1:7001,host2:7002,host3:7003`
- **THEN** RedisGate SHALL 正确解析出三个节点并创建集群客户端
- **AND** 不抛出 `ValueError: Port could not be cast to integer value` 异常

#### Scenario: 单机 Redis URL 正常工作
- **WHEN** `redis_url` 配置为 `redis://localhost:6379/0`（不含逗号）
- **THEN** RedisGate SHALL 创建单机 Redis 客户端
- **AND** 行为与修改前保持一致

### Requirement: 统一使用异步 Redis 客户端
Redis 闸门模块 SHALL 全部使用异步 Redis 客户端（`redis.asyncio`），包括单机模式和集群模式，确保所有 Redis 操作都是非阻塞的。

#### Scenario: 单机模式使用异步客户端
- **WHEN** 配置为单机 Redis
- **THEN** `self._redis` SHALL 是 `redis.asyncio.Redis` 实例
- **AND** 所有方法（`acquire`、`_release_script_exec`、`get_current_inflight`）使用 `await` 调用均可正常工作

#### Scenario: 集群模式使用异步客户端
- **WHEN** 配置为 Redis 集群
- **THEN** `self._redis` SHALL 是 `redis.asyncio.cluster.RedisCluster` 实例
- **AND** 所有方法（`acquire`、`_release_script_exec`、`get_current_inflight`）使用 `await` 调用均可正常工作

### Requirement: Lua 脚本在集群模式下可用
Redis 闸门的并发控制 SHALL 在集群模式下正常工作，使用 Lua 脚本实现的原子操作 SHALL 正确执行。

#### Scenario: 集群模式下获取许可成功
- **WHEN** 当前并发数小于 `max_in_flight`
- **THEN** `acquire` 方法 SHALL 成功获取许可并增加计数器
- **AND** 返回值为 1

#### Scenario: 集群模式下获取许可失败
- **WHEN** 当前并发数已达到 `max_in_flight`
- **THEN** `acquire` 方法 SHALL 返回 0
- **AND** 进入等待重试循环

#### Scenario: 集群模式下释放许可
- **WHEN** 调用释放许可操作
- **THEN** 计数器 SHALL 减 1
- **AND** 不小于 0

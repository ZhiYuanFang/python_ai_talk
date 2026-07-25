## ADDED Requirements

### Requirement: ClusterNode startup nodes
Redis 闸门在集群模式下 SHALL 使用 `redis.asyncio.cluster.ClusterNode` 实例列表作为 `RedisCluster` 的 `startup_nodes`，不得传入裸 `dict`。

#### Scenario: 集群客户端创建成功
- **WHEN** `redis_url` 含逗号且解析出至少一个有效节点
- **THEN** `RedisGate` 初始化 SHALL 成功创建 `redis.asyncio.cluster.RedisCluster`
- **AND** SHALL NOT 抛出 `AttributeError: 'dict' object has no attribute 'host'`

#### Scenario: 单机模式不受影响
- **WHEN** `redis_url` 不含逗号
- **THEN** `RedisGate` SHALL 仍创建 `redis.asyncio.Redis` 单机客户端

### Requirement: 多节点逗号 URL 完整解析
Redis 闸门 SHALL 正确解析形如 `redis://host1:7001,host2:7002,host3:7003` 的 URL，包括无 `redis://` scheme 的后续节点段。

#### Scenario: 三节点全部进入 startup_nodes
- **WHEN** `redis_url` 为 `redis://host1:7001,host2:7002,host3:7003`
- **THEN** `startup_nodes` SHALL 包含三个 `ClusterNode`（host/port 分别为三组）
- **AND** SHALL NOT 仅包含第一个节点

#### Scenario: 首节点携带密码时共享
- **WHEN** 首节点 URL 含密码（如 `redis://:secret@host1:7001,host2:7002`）
- **THEN** 创建 `RedisCluster` 时 SHALL 使用该密码参数

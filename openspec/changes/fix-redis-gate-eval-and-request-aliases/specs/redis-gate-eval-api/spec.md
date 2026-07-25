## ADDED Requirements

### Requirement: eval 使用 redis-py 兼容签名
Redis 闸门执行 Lua 时 SHALL 使用 redis-py 支持的 `eval(script, numkeys, *keys_and_args)`（或等价的 `register_script` + `keys`/`args` 调用约定），不得向 `eval` 传入不被支持的 `keys=`/`args=` 关键字参数。

#### Scenario: acquire 不再因 keys 关键字失败
- **WHEN** `RedisGate.acquire` 执行获取许可的 Lua 脚本
- **THEN** 调用 SHALL NOT 抛出 `unexpected keyword argument 'keys'`
- **AND** 在 Redis 可用且未超限时 SHALL 成功获取许可（返回成功路径）

#### Scenario: release 不再因 keys 关键字失败
- **WHEN** 上下文退出触发释放许可
- **THEN** 释放 Lua 调用 SHALL NOT 因 `keys=` 关键字参数失败
- **AND** 成功路径下计数器 SHALL 按脚本逻辑递减

### Requirement: 单机与集群共用同一调用方式
单机 `Redis` 与集群 `RedisCluster` 客户端 SHALL 使用同一套 eval/脚本调用封装，避免仅某一模式可用。

#### Scenario: 集群模式下 Clinic 流式可过闸门
- **WHEN** 服务配置为集群 `redis_url` 且 LLM 流式调用进入闸门
- **THEN** `acquire`/`release` SHALL 可完成而不因 eval API 错误中断 ASGI 任务组

## Context

`fix-redis-clusternode-and-chroma-telemetry` 修复了集群 `startup_nodes` 类型后，生产 Clinic SSE 前进到 `RedisGate.acquire`，随即因 `eval(..., keys=..., args=...)` 与 redis-py API 不符而失败；`finally` 中 release 再次失败并打 WARNING。同窗口出现 Pydantic `UnsupportedFieldAttributeWarning`（`validation_alias=AliasChoices(...)`）以及外网 `POST /v1/analyze/intent` 422；内网 Go 发 snake 的 clinic 能过校验，说明 422 更可能来自外网 body 或 alias 在部分路径失效，需稳住双收并记录校验详情。

约束：不改 Go；单机/集群闸门行为一致；保持中文注释。

## Goals / Non-Goals

**Goals:**
- `acquire`/`release` 的 Lua 调用在 redis-py 5+/集群客户端上成功执行
- 消除（或显著减少）`device_no` 相关 `UnsupportedFieldAttributeWarning`
- Intent/Clinic/Tip 对 `device_no` 与 `deviceNo` 均可校验通过
- 422 时日志可见校验失败摘要

**Non-Goals:**
- 事件字典为空业务修复
- 修改 Go/Flutter
- 更换 Redis 闸门算法或 Key 格式
- 升级 pydantic/fastapi 主版本（除非为消警告所必需且风险低）

## Decisions

### 决策 1：Lua 调用用位置参数（或 register_script）

**选择**：统一为  
`await self._redis.eval(script, 1, key, *args)`  
（release 无 ARGV 时 `eval(script, 1, key)`）。  
可选同时用 `register_script` 缓存 SHA，但非必须。

**替代**：继续 `keys=`/`args=` —— 与 `ScriptCommands.eval` 签名冲突，排除。

**理由**：与 redis-py 公开签名一致；单 key 脚本在集群同 slot 安全。

### 决策 2：alias 用 Annotated 附着

**选择**：  
`device_no: Annotated[str, Field(validation_alias=AliasChoices("device_no", "deviceNo"), ...)]`  
并保留 `ConfigDict(populate_by_name=True)`（或等价 `validate_by_name`）。

**替代**：去掉全部 alias、只认 snake —— 对 Go 足够，但外网 camel 调用方会继续 422。

**理由**：对齐 Pydantic「Field 元数据须经 Annotated/赋值生效」的新警告路径；双收仍要。

### 决策 3：422 日志

**选择**：在 FastAPI 层增加 `RequestValidationError` 处理器（或中间件），对 `/v1/analyze/*`、`/v1/clinic*`、`/v1/tip*` 记 WARNING，内容含 path + `exc.errors()` 摘要（截断），不回传敏感扩展。

**替代**：只靠客户端看响应 body —— 生产排障慢。

## Risks / Trade-offs

| 风险 | 缓解 |
|---|---|
| 集群 EVAL 与 key 路由 | 单 key；失败时日志带 key |
| Annotated 改法在旧 pydantic 行为差异 | Dockerfile 已钉 fastapi 0.115 + pydantic 2.x；本地冒烟 snake/camel |
| 422 日志噪声 | 仅 WARNING + 截断；不含完整 body |

## Migration Plan

1. 改 redis_gate + schemas + 422 handler  
2. 重建镜像；打 clinic stream 与 intent snake/camel  
3. 回滚：回退镜像  

## Open Questions

1. Tip 请求中若还有其他带 AliasChoices 的字段，是否一并改 Annotated？（建议：同文件内所有同类字段一次改完）

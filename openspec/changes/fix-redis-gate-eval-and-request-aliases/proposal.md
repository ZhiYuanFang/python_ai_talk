## Why

Clinic 流式在 Redis 集群连接修复后仍崩溃：`RedisGate` 调用 `eval(..., keys=..., args=...)`，与 redis-py 实际签名 `eval(script, numkeys, *keys_and_args)` 不匹配，acquire/release 均失败。同时 Pydantic 对新版 schema 生成路径发出 `validation_alias`/`AliasChoices` 无效警告；外网 Intent 出现 422，需稳住 snake/camel 双收并便于排查校验失败原因。

## What Changes

- 修正 `redis_gate.py` 的 Lua `eval`/`eval` 释放调用为 redis-py 兼容写法（位置参数或 `register_script`）
- 修正 Intent/Clinic/Tip 请求模型中 `device_no` 等字段的 alias 附着方式，消除 `UnsupportedFieldAttributeWarning`，并保证 `device_no`/`deviceNo` 双收在 FastAPI 入站路径有效
- 对请求体校验失败（422）增加简要日志（记录 `detail` 摘要），便于区分缺字段 vs 别名问题
- **不**修改 Go 客户端序列化（内部契约仍为 snake_case）
- **不**处理事件字典为空的业务降级（另议）

## Capabilities

### New Capabilities

- `redis-gate-eval-api`: Redis 闸门 Lua 脚本调用与 redis-py `eval`/`register_script` API 对齐，单机与集群均可 acquire/release
- `request-alias-annotated`: 入站请求模型以 Annotated/有效 Field 方式声明 validation_alias，消除无效警告并稳住双收
- `request-validation-422-log`: 意图/诊疗等关键入站 422 时记录校验失败摘要，便于排障

### Modified Capabilities

（无：`openspec/specs/` 下无已归档主规格需 delta）

## Impact

- **代码**：`app/shared/redis_gate.py`；`app/feeding/schemas/intent.py`；`app/tip/schemas/tip.py`；可选 `app/main.py` 或异常处理器/路由层 422 日志
- **API**：无契约字段变更；行为上 Clinic 流式可过闸门；Intent 双收更稳
- **依赖**：无新增包
- **兄弟仓**：Go/Flutter 无需改动（Go 已发 snake）

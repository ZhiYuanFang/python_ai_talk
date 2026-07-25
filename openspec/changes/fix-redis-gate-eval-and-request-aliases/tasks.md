## 1. Redis 闸门 eval API

- [x] 1.1 修改 `app/shared/redis_gate.py`：`acquire` 中 `eval` 改为 `eval(script, 1, key, max_in_flight)`（或 register_script 等价写法）
- [x] 1.2 同步修正 `_release_script_exec` 的 `eval` 调用签名
- [x] 1.3 用 mock Redis/RedisCluster 冒烟：调用不再出现 `unexpected keyword argument 'keys'`

## 2. 请求模型 alias Annotated

- [x] 2.1 修改 `IntentRequest` / `ClinicRequest` 的 `device_no` 为 `Annotated[..., Field(validation_alias=AliasChoices(...))]`，保留 populate_by_name
- [x] 2.2 修改 `TipRequest`（及同文件其他 AliasChoices 字段）同样改为 Annotated
- [x] 2.3 验证 snake/camel 均可 `model_validate`；导入时用 warnings 捕获确认无 UnsupportedFieldAttributeWarning

## 3. 422 校验日志

- [x] 3.1 在 `app/main.py`（或合适模块）注册 `RequestValidationError` 处理器，记录 path + errors 摘要
- [x] 3.2 确认 422 状态码与响应体行为不变

## 4. 收尾

- [x] 4.1 确认无残留 `eval(..., keys=` 调用
- [x] 4.2 简要确认兄弟仓 Go 仍发 snake、无需改动

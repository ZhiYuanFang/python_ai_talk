## ADDED Requirements

### Requirement: 记录请求体校验失败摘要
当 FastAPI 因请求体/查询校验失败返回 422 时，服务 SHALL 记录一条 WARNING（或更高）级别日志，包含请求 path 与校验错误摘要（来自 `RequestValidationError.errors()`，可截断），以便区分缺字段与别名问题。

#### Scenario: Intent 422 可在服务日志中定位
- **WHEN** `POST /v1/analyze/intent` 因缺少必填字段或字段类型错误导致 422
- **THEN** 服务日志 SHALL 包含 path `/v1/analyze/intent`（或完整 path）以及至少一条错误位置/类型信息
- **AND** HTTP 响应仍为 422（行为不改变对外状态码）

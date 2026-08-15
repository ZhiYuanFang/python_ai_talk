## ADDED Requirements

### Requirement: filter 支持 ignoreTimeRange 强制忽略时间窗

Python 调用的 Go `GET /device/history/api/filter` SHALL 接受可选查询参数 `ignoreTimeRange`。未传或为假时，时间筛选语义 MUST 与现网一致（调用方传入的正数 `startTime`/`endTime` 施加对应条件）。为真时，服务端 MUST 完全忽略请求中的 `startTime` 与 `endTime`（即使均为正数）；`deviceNo`、`eventIds`、`remark`、`limit` 与既有排序 MUST 保持不变。本参数为 additive 扩展，MUST NOT 改变未传参时的旧行为。

#### Scenario: 未传 ignoreTimeRange 时沿用时间窗

- **WHEN** Python 调用 filter 且未传 `ignoreTimeRange`，并传入正数 `startTime`/`endTime`
- **THEN** 结果 MUST 仍受该时间窗约束（与开关上线前一致）

#### Scenario: ignoreTimeRange 为真时忽略已填时间

- **WHEN** Python 以 `ignoreTimeRange=true` 调用 filter，且同时传入非零 `startTime` 与/或 `endTime`
- **THEN** 返回结果 MUST NOT 因这些时间参数被过滤
- **AND** `eventIds`、`remark`、`limit` 筛选 MUST 仍生效

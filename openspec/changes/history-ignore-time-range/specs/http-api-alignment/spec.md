## ADDED Requirements

### Requirement: get_filtered_history_events 透传 ignoreTimeRange

`HttpClient.get_filtered_history_events` SHALL 增加可选参数 `ignore_time_range`（默认 false / 未传视为 false）。当该参数为真时，请求 MUST 在 query 中包含 `ignoreTimeRange=true`；为假或未传时 MUST NOT 写入该 query 键。路径仍为 `GET /device/history/api/filter`；`deviceNo`、`eventIds`、`startTime`、`endTime`、`limit`、`remark` 的既有序列化规则 MUST 保持不变。

#### Scenario: 为真时写入 query

- **WHEN** 调用 `get_filtered_history_events(..., ignore_time_range=True)`，且同时传入非空 `start_time`/`end_time`
- **THEN** 发出的 HTTP 请求 MUST 包含 query `ignoreTimeRange=true`
- **AND** MUST 仍可包含 `startTime`/`endTime`（由 Go 侧按开关忽略）

#### Scenario: 默认不传该 query

- **WHEN** 调用 `get_filtered_history_events` 且未传 `ignore_time_range` 或为 false
- **THEN** 请求 query MUST NOT 包含 `ignoreTimeRange`
- **AND** 时间与其它筛选参数行为 MUST 与本变更前一致

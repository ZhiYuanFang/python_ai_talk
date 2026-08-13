## ADDED Requirements

### Requirement: 非流式 clinic 与 stream 同源
系统 SHALL 在提供 `/v1/clinic/stream` 的同时提供非流式 `POST /v1/clinic`，二者 MUST 共用 `clinic_graph` 与 `ClinicRequest` 字段语义。非流式细节以 capability `clinic-sync-http` 为准。

#### Scenario: stream 路径保持
- **WHEN** 客户端调用 `/v1/clinic/stream`
- **THEN** 系统 SHALL 仍以 SSE 返回 thinking 与 answer
- **AND** SHALL NOT 改走 intent_graph

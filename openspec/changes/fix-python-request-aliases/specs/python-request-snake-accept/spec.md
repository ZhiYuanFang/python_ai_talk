## ADDED Requirements

### Requirement: Intent 请求接受 snake_case device_no

`IntentRequest` SHALL 接受 JSON 字段名 `device_no`（snake_case）作为设备编号入参。若保留 camelCase 过渡别名，MUST 同时接受 `deviceNo`，且 MUST NOT 在仅发送 `device_no` 时返回 422。

#### Scenario: Go snake body 通过 Intent 校验

- **WHEN** 调用方 POST 意图分析接口，body 含 `"device_no": "<非空>"` 及合法的 `text`、`model`
- **THEN** Pydantic SHALL 成功解析为 `IntentRequest`，且 `device_no` 属性等于该值
- **AND** SHALL NOT 因缺少 `deviceNo` 而返回 422

#### Scenario: 过渡双收 camel deviceNo（若启用）

- **WHEN** 调用方 POST 意图分析接口，body 使用 `"deviceNo"` 而非 `device_no`
- **THEN** 系统 SHALL 仍能成功解析（过渡兼容）或按实现选择仅 snake；若选择仅 snake，本场景不适用但前一场景 MUST 成立

### Requirement: Clinic 请求接受 snake_case device_no

`ClinicRequest` SHALL 接受 JSON 字段名 `device_no`。MUST NOT 因只认 `deviceNo` alias 而拒绝 Go snake body。

#### Scenario: Go snake body 通过 Clinic 校验

- **WHEN** 调用方 POST 诊疗接口，body 含 `"device_no": "<非空>"` 及合法的 `question`、`model`
- **THEN** Pydantic SHALL 成功解析为 `ClinicRequest`
- **AND** SHALL NOT 因缺少 `deviceNo` 而返回 422

### Requirement: Tip 请求接受 snake_case 设备与上下文字段

`TipRequest` SHALL 接受 JSON 字段名 `device_no`、`baby_age_months`、`current_time`（均为 snake_case）。MUST NOT 因只认 `deviceNo` / `babyAgeMonths` / `currentTime` 而拒绝 Go `PythonAIClient.TipStream` 的现有序列化 body。

#### Scenario: Go TipStreamRequest snake body 通过校验

- **WHEN** 调用方 POST tip stream 接口，body 含 `device_no`、`baby_age_months`、`current_time`（及合法的 `event_id`、`event_name`、`model`）
- **THEN** Pydantic SHALL 成功解析为 `TipRequest`
- **AND** SHALL NOT 因缺少 camelCase 别名键而返回 422

### Requirement: 禁止以改 Go 客户端为 camel 作为修复手段

修复本能力时，实现 MUST 修改 Python 入站模型（或等价服务端校验），MUST NOT 将 `go_ai_talk` 的 `PythonAIClient` JSON 标签改为 camelCase 以绕过校验。

#### Scenario: 内部契约保持 snake

- **WHEN** 评审本变更的实现 diff
- **THEN** Go `PythonAIClient` 请求体字段标签 SHALL 仍为 snake_case（如 `device_no`）
- **AND** Python 侧 SHALL 已能接受上述 snake 键

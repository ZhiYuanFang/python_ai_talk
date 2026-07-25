## Why

Go `PythonAIClient` 对 Python 内部 API 统一发送 **snake_case** JSON（如 `device_no`、`baby_age_months`、`current_time`），但 Python 侧 `IntentRequest` / `ClinicRequest` / `TipRequest` 对部分字段设置了仅 camelCase 的 `Field(alias=...)`，且未开启 `populate_by_name`，导致 Pydantic 校验只认 `deviceNo` 等别名，Go 请求被 **422** 拒绝。需立即对齐，使现有 Go snake body 可通过校验，避免意图/诊疗/小贴士链路全部失败。

## What Changes

- 修正 `IntentRequest`、`ClinicRequest`、`TipRequest` 的字段别名策略：内部契约以 **snake_case 字段名为准**；过渡期可双收 camel alias，或去掉「只认 camel」的 alias。
- **不**修改 Go `PythonAIClient` 为 camelCase（锁定：Go↔Python 内部 API 统一 snake_case）。
- 修正本仓或关联 Go OpenSpec 中「应发 `device_no` 但 Python 只认 camel」的矛盾表述（若存在）。
- 本变更不涉及月龄/时间字段删除（由后续 `tip-derive-baby-age` 处理）；不改动 Chat 宿主；App 对外 Flutter↔Go 仍可 camel。

## Capabilities

### New Capabilities

- `python-request-snake-accept`: Python 入站请求模型接受 Go 侧 snake_case JSON（`device_no` 等），并可过渡双收 camel alias，保证 Intent / Clinic / Tip 校验通过。

### Modified Capabilities

- （无）当前 `openspec/specs/` 下无已归档主规格需 delta。

## Impact

- **Python**：`app/feeding/schemas/intent.py`（`IntentRequest`、`ClinicRequest`）、`app/tip/schemas/tip.py`（`TipRequest`）；相关路由/文档注释中的字段说明。
- **Go**：无需改 `python_ai_client.go` 序列化；可选修正 `go_ai_talk` 内矛盾 OpenSpec 表述。
- **Flutter / Chat**：不在本变更范围。
- **后续依赖**：`tip-derive-baby-age` 依赖本变更完成后再瘦身 tip 字段。

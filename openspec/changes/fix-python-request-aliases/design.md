## Context

Go `internal/services/voice/python_ai_client.go` 对 Python 内部 HTTP API 使用 snake_case JSON 标签，例如：

- Intent / Clinic：`device_no`
- Tip：`device_no`、`baby_age_months`、`current_time`

Python Pydantic 模型现状（问题根因）：

| 模型 | 字段 | 当前 alias | 默认校验行为 |
|------|------|------------|--------------|
| `IntentRequest` | `device_no` | `deviceNo` | 只认 alias，拒收 `device_no` |
| `ClinicRequest` | `device_no` | `deviceNo` | 同上 |
| `TipRequest` | `device_no` / `baby_age_months` / `current_time` | `deviceNo` / `babyAgeMonths` / `currentTime` | 同上 |

Pydantic v2 在设置 `Field(alias=...)` 且未 `populate_by_name=True` 时，入站 JSON **只接受 alias**，导致 Go snake body → HTTP 422。

利益相关方：voice-service（Go 调用方）、python_ai_talk（校验方）；App 对外 Flutter↔Go camel 不在本变更。

## Goals / Non-Goals

**Goals:**

- Go 现有 `PythonAIClient` snake_case body 对 Intent / Clinic / Tip 请求均可过 Pydantic 校验。
- 内部 API 命名契约明确为 **snake_case**；文档与实现一致。
- 过渡期可双收 camel alias，避免外部/旧调用方瞬时断裂（若有）。

**Non-Goals:**

- 不把 Go `PythonAIClient` 改成 camelCase。
- 不删除 tip 的 `baby_age_months` / `current_time` 字段（留给 `tip-derive-baby-age`）。
- 不改动 Chat 宿主（仍走 history SSE）。
- 不改 Flutter↔Go App API 的 camelCase。
- 不新增测试文件（仓库约定）。

## Decisions

### 决策 1（锁定）：Go↔Python 内部 API 统一 snake_case

- **方案**：Python 请求模型以 snake_case 字段名为权威入站键；**禁止**为迁就 alias 而改 Go 客户端为 camel。
- **理由**：Go 客户端与多数内部字段已是 snake；改 Go 会扩大不一致面并与跨仓锁定决策冲突。
- **备选**：Go 改 camel — **排除**。

### 决策 2：Python 过渡双收（推荐）或去掉只认 camel 的 alias

- **方案 A（推荐）**：对带 camel alias 的字段使用 `AliasChoices("device_no", "deviceNo")`（及 tip 的月龄/时间对应双名），并设置 `model_config = ConfigDict(populate_by_name=True)`（或等价），使 snake 与 camel 均可反序列化；模型属性仍用 snake 访问。
- **方案 B**：直接去掉 `alias=`，仅接受 snake_case（若确认无 camel 调用方）。
- **拍板**：优先 **方案 A**（双收过渡）；若实现时确认全链路仅 Go snake，可退化为方案 B，但 MUST 保证 snake 通过。
- **备选**：仅 `populate_by_name=True` 保留单一 alias — 在 Pydantic v2 下通常可同时接受字段名与 alias，亦可作为最小补丁；若单开仍只认 camel，则必须上 `AliasChoices`。

### 决策 3：覆盖范围仅三模型相关字段

- **方案**：至少修正 `IntentRequest.device_no`、`ClinicRequest.device_no`、`TipRequest` 的 `device_no` / `baby_age_months` / `current_time`。
- **理由**：与 Go 422 现场一致；其它响应模型/出站 camel（Python→Go history query）不在本变更。

### 决策 4：矛盾 OpenSpec 表述的修正策略

- **方案**：若 `go_ai_talk` 或本仓 change 文档出现「Go 应发 `device_no` 但 Python 只认 camel」类矛盾，修正为「内部请求 JSON MUST 为 snake_case；Python MUST 接受 snake（可双收 camel）」。
- **已知相关**：`go_ai_talk/openspec/changes/fix-python-api-alignment` 已写 Go 发 `device_no`，与本决策一致；实现时再 grep 确认无「Py 只认 camel」反向表述。
- **本变更不改写** App 侧 Flutter camel 描述（那是对外 API）。

### 决策 5（边界锁定，供后续 change 引用）

以下来自 explore，本变更 **不实现**，但写入以免歧义：

1. 月龄由 Python 在 `fetch_baby_profile` 后根据 birthday 自算（`tip-derive-baby-age`）。
2. `current_time` 由 Python 写提示词时用 `time.time()`（或本地可读时间）生成，不要求 Go/Flutter 传入。
3. 不动 Chat 宿主。
4. App 对外仍可 camel；本变更焦点是 Go↔Python 入站校验。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 双收掩盖错误调用方长期不收敛 | 文档标明 snake 为权威；后续 change 可删 camel alias |
| 仅改 alias、漏改路由层二次校验 | 以 schema 校验为准；手测 Intent/Clinic/Tip 各一请求 |
| 与后续 tip 字段删除冲突 | 本变更不删字段；`tip-derive-baby-age` 依赖本 change 完成后再瘦身 |

## Migration Plan

1. 部署 Python 服务（仅 schema 变更，无 DB migration）。
2. 用 Go 现有 snake body 回归：`/v1/analyze/intent`（或 stream）、clinic stream、tip stream。
3. 回滚：还原 schema alias 配置即可；Go 无需联动回滚。

## Open Questions

- 无阻塞问题。过渡双收 vs 仅 snake 由实现按决策 2 选择，验收标准以「Go snake 通过」为准。

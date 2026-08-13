## ADDED Requirements

### Requirement: 意图路径不得调用 clinic agent
意图图与 `/v1/analyze/intent`、`/intent/stream` SHALL NOT 调用 `call_clinic_agent` 或 `clinic_graph`。陪伴会话的读写 SHALL 仅由 clinic/tip 路由承担。`feeding` 模块 MUST NOT 导入 `clinic` 模块。

#### Scenario: conversation 不读写陪伴会话
- **WHEN** 意图结果为 conversation
- **THEN** 本请求 SHALL NOT `append_turn` 到 companion session
- **AND** SHALL NOT 执行 clinic 隐式飞轮

#### Scenario: feeding 不导入 clinic
- **WHEN** 检查 feeding 意图图依赖
- **THEN** SHALL NOT 存在对 `app.clinic` 的导入（含 call_clinic_agent）

## REMOVED Requirements

### Requirement: Intent clinic agent reads companion chat context
**Reason**: 意图不再嵌入 clinic agent。
**Migration**: 陪伴上下文仅由 `/v1/clinic` 与 `/v1/clinic/stream` 读取。

### Requirement: Intent clinic agent writes companion turn after success
**Reason**: 意图不再写陪伴会话。
**Migration**: 成功陪伴轮次由 clinic 路由 `append_turn`。

### Requirement: Implicit feedback before intent clinic generation
**Reason**: 意图路径不再做 clinic 隐式反馈。
**Migration**: 隐式反馈保留在 clinic_graph 入口。

### Requirement: Intent clinic agent uses bestie clinic_answer generation
**Reason**: 意图不再生成 clinic_answer。
**Migration**: 专家陪伴提示词仅用于 clinic/tip。

### Requirement: Non-clinic intent paths leave companion session untouched
**Reason**: 全部意图路径均不再接触陪伴会话，本条与「意图不得调用 clinic」合并。
**Migration**: 见新增 Requirement「意图路径不得调用 clinic agent」。

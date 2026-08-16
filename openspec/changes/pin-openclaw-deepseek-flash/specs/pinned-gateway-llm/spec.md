## ADDED Requirements

### Requirement: 门禁忽略 Go 的 LLM 注模头

`POST /agent-gate/v1/chat/completions` 在校验 G 并转发内部 OpenClaw 时，MUST NOT 将请求头 `x-openclaw-model` 转发至 Gateway。系统 SHALL 继续转发 `x-openclaw-session-key` 与 `x-pangbao-api-token`（若存在）。`Authorization` 仍替换为内部 `INTERNAL_GATEWAY_TOKEN`。

#### Scenario: 带注模头进入门禁

- **WHEN** 客户端以有效 G 调用门禁，并携带 `x-openclaw-model: zhipu/glm-4.7-flash`（或任意非空值）
- **THEN** 门禁转发至 Gateway 的请求 MUST NOT 包含 `x-openclaw-model`
- **AND** 若原请求含 `x-openclaw-session-key` / `x-pangbao-api-token`，转发请求 MUST 仍包含它们

#### Scenario: 无注模头仍可转发

- **WHEN** 客户端以有效 G 调用门禁且未带 `x-openclaw-model`
- **THEN** 门禁 MUST 仍将 body 与其它约定头转发至 Gateway（行为与剥头前一致，仅无该头）

### Requirement: OpenClaw 默认 LLM 钉死 DeepSeek V4 Flash

`deploy/openclaw/openclaw.json5` 中 `agents.defaults` SHALL 将默认模型配置为 `deepseek/deepseek-v4-flash`（`model` 为字符串或含 `primary` 的对象，与 OpenClaw 2026.7.1-2 AgentsSchema 兼容的形式）。Intent / Clinic / Care Alert 在无请求级 LLM override 时 MUST 使用该默认模型（经门禁路径时因无 `x-openclaw-model` 而生效）。

#### Scenario: defaults 含 flash

- **WHEN** 审查 `openclaw.json5` 的 `agents.defaults`
- **THEN** 其中 MUST 指定默认 LLM 为 `deepseek/deepseek-v4-flash`（带 `deepseek/` provider 前缀）

### Requirement: README 标明写死 flash 与忽略 Go 注模

根 `README.md` SHALL 说明：编排 LLM 由 OpenClaw 配置钉死为 `deepseek/deepseek-v4-flash`；门禁不转发 `x-openclaw-model`，故 Go 注模暂时无效；`body.model` 的 `openclaw/intent|clinic|care_alert` 仍用于选择 agent。

#### Scenario: 运维阅读 README

- **WHEN** 运维阅读 OpenClaw / 门禁相关启动或架构说明
- **THEN** 文档 MUST 写明 LLM 写死 flash 与 Go 头被忽略
- **AND** MUST NOT 将「经门禁的 x-openclaw-model 控制实模」表述为当前有效行为

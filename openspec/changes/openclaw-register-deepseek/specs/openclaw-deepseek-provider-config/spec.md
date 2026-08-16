## ADDED Requirements

### Requirement: json5 显式登记 DeepSeek provider

`deploy/openclaw/openclaw.json5` SHALL 在 `models` 下以 merge 模式登记 `deepseek` provider（含可解析的 API 基址与从环境变量读取的 API Key 引用），并至少声明模型 id `deepseek-v4-flash`。`agents.defaults` SHALL 继续以 `deepseek/deepseek-v4-flash` 为 primary，并在 `agents.defaults.models`（或等价允许表）中登记该 ref。

#### Scenario: 配置含 deepseek-v4-flash

- **WHEN** 审查 `openclaw.json5`
- **THEN** 存在 `models.providers.deepseek` 且其模型列表含 `deepseek-v4-flash`
- **AND** `agents.defaults.model` 指向 `deepseek/deepseek-v4-flash`
- **AND** 文件中 MUST NOT 出现明文 DeepSeek API Key

### Requirement: README 说明显式登记与 recreate

根 `README.md` SHALL 说明 OpenClaw 已在 json5 显式登记 DeepSeek；修改该配置后对 Gateway 执行 recreate（无需因本项 rebuild 镜像）。

#### Scenario: 运维按 README 生效配置

- **WHEN** 运维更新 `openclaw.json5` 中的 models 段
- **THEN** 文档指示通过 compose recreate/restart 使 Gateway 加载新配置

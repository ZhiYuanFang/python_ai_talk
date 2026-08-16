## ADDED Requirements

### Requirement: pangbao-tools manifest 声明 contracts.tools

`deploy/openclaw/plugins/pangbao-tools/openclaw.plugin.json` MUST 包含 `contracts.tools`，且其值 MUST 为非空字符串数组，列出该插件实现中全部 agent tool 名称（至少包括：`history_create`、`history_update`、`history_delete`、`history_end_latest`、`history_filter`、`history_list`、`history_options`、`baby_profile`、`flywheel_intent_retrieve`、`flywheel_intent_record`、`flywheel_clinic_retrieve`、`flywheel_clinic_record`、`clinic_judge_implicit_acceptance`、`emit_care_cards`）。`contracts.tools` MUST NOT 使用布尔 `true` 或通配符代替显式名称列表。

#### Scenario: manifest 含显式工具契约

- **WHEN** 读取仓库中的 `openclaw.plugin.json`
- **THEN** JSON 中 SHALL 存在路径 `contracts.tools`
- **AND** `contracts.tools` SHALL 为数组且包含 `history_create` 与 `emit_care_cards`

### Requirement: Gateway 可将业务 allowlist 解析为可调用 tool

在 OpenClaw Gateway 已启用 `pangbao-tools`、插件 dist 可加载、且上述 `contracts.tools` 已生效的前提下，对配置了显式 `agents.*.tools.allow`（含 `history_create` 等业务名）的 agent 发起 `POST /v1/chat/completions` 时，系统 MUST NOT 因「explicit tool allowlist 解析后无任何 registered tools matched」而在 prompt 阶段失败。

#### Scenario: intent chat 不再报零 callable tools

- **WHEN** Gateway 使用已更新的 pangbao-tools manifest 并完成重启
- **AND** 客户端以有效 Gateway token 调用 `model=openclaw/intent` 的 chat completions
- **THEN** 错误响应（若有）MUST NOT 包含文案 `No callable tools remain after resolving explicit tool allowlist`
- **AND** MUST NOT 包含 `no registered tools matched` 针对该业务 allowlist 的失败（上游 LLM 或 Python tools HTTP 错误另论）

### Requirement: 运维文档说明 contracts 与重启

插件或根 README SHALL 说明：OpenClaw 注册 agent tools 依赖 manifest `contracts.tools`；修改该文件后须 restart/recreate Gateway；一般不必因仅改 manifest 而 rebuild Gateway 镜像。

#### Scenario: 文档可复核

- **WHEN** 阅读 `deploy/openclaw/plugins/README.md` 或根 README 中 OpenClaw 插件相关段落
- **THEN** 文档 SHALL 提及 `contracts.tools`
- **AND** SHALL 提及改 manifest 后需重启 Gateway

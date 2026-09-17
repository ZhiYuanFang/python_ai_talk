## ADDED Requirements

### Requirement: Growth trajectory system prompt requires Chinese internal thinking

成长轨迹共用 system 提示（`GROWTH_TRAJECTORY_SYSTEM_PROMPT`）SHALL 明确要求模型在内部思考 / 提供商 reasoning 通道中使用中文。该约束 MUST 出现在 system 正文中，且 MUST 应用于所有使用该 system 的成长轨迹 LLM 调用（含 confirm、plan、ask 兜底、generate）。系统 MUST NOT 仅依赖 user message 来约束思考语言。

#### Scenario: System prompt text includes Chinese-thinking constraint

- **WHEN** 读取成长轨迹 system 提示常量
- **THEN** 正文中 SHALL 包含要求内部思考（reasoning）使用中文的明确约束

#### Scenario: Confirm / plan / generate share the same system

- **WHEN** `confirm_prior`、`plan_next`（含 ask 兜底）或 `generate` 发起 LLM 调用
- **THEN** 调用 SHALL 使用含「内部思考用中文」约束的同一成长轨迹 system 提示

### Requirement: Answer schema language constraints remain

在新增思考语言约束后，成长轨迹 system / 各阶段 user 提示对最终输出的既有语言与 schema 要求 SHALL 保持有效：结构化字段中面向家长的文案与选项仍须为中文（或按既有 schema 约定），Markdown 轨迹仍面向中文家长阅读。新增思考语言约束 MUST NOT 取消这些最终输出约束。

#### Scenario: Final output still Chinese-oriented

- **WHEN** plan / confirm / ask 要求 JSON，或 generate 要求 Markdown
- **THEN** 既有「中文理由 / 中文选项 / 家长可读 Markdown」类规则 SHALL 仍存在于对应提示词中

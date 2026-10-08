## ADDED Requirements

### Requirement: All LLM calls on outbound SSE paths stream native reasoning

当请求走对外 SSE 入口（clinic `/v1/clinic/stream`、intent `/v1/analyze/intent/stream`、care-alert `/v1/care-alert/analyze/stream`、growth-trajectory turn）时，该请求处理链上每一次 LLM 调用（含主回答、意图分类、needs_history / data_requirement 等判定节点、pending 澄清等）SHALL 使用 `llm_client.stream` 且 `thinking_enabled=True`，并将提供商 reasoning 增量映射为 SSE `type=thinking` 内容透出。SHALL NOT 在上述 SSE 路径上对这类 LLM 调用使用 `invoke` 黑盒后再伪造 thinking。同步非 SSE 接口（如 `/v1/clinic`、`/v1/analyze/intent`）MAY 继续使用 `invoke`。

#### Scenario: Clinic gate LLM reasoning visible

- **WHEN** 客户端调用 `/v1/clinic/stream` 且执行 `judge_needs_history`（或 `judge_data_requirement`）并产生非空 reasoning
- **THEN** 客户端 SHALL 在该节点返回最终状态更新之前收到对应的 `type=thinking` 增量（模型 reasoning），而不仅是编排字幕

#### Scenario: Intent classify LLM reasoning visible

- **WHEN** 客户端调用 `/v1/analyze/intent/stream` 冷启动路径执行 `classify_intent` 并产生非空 reasoning
- **THEN** 客户端 SHALL 收到 `type=thinking` 的 reasoning 增量，SHALL NOT 仅在分类完成后才出现与模型思考相关的可见进度

#### Scenario: Sync non-SSE may invoke

- **WHEN** 客户端调用非流式 `/v1/analyze/intent` 或 `/v1/clinic`
- **THEN** 系统 MAY 对判定/分类/回答使用 `invoke`，且不要求推送 SSE thinking

### Requirement: Multiple reasoning segments per SSE request are allowed

单次对外 SSE 请求中，系统 MAY 推送多段模型 reasoning（例如 clinic：门禁 reasoning 与主回答 reasoning 分属不同段落）。编排字幕与 LLM reasoning 仍共用 `type=thinking`；段首 `\r` 开泡约定（编排字幕与本段首次 LLM thinking 增量）SHALL 继续适用；后续同段 LLM thinking 增量 MUST NOT 再强制加 `\r`。

#### Scenario: Clinic multi-segment thinking

- **WHEN** `/v1/clinic/stream` 先后执行门禁 LLM 与主回答 LLM，且两段均有 reasoning
- **THEN** 客户端 SHALL 能观察到至少两段可区分的 thinking 内容（经由段首 `\r` 或编排字幕分隔），且回答仍以 `type=answer` 推送

### Requirement: No LLM short-circuit paths do not invent reasoning

无 LLM 的短路（如意图缓存命中、精确父名消歧、模板 `speak_history`）SHALL NOT 伪造模型 reasoning；MAY 仅推送编排字幕（若该路径有节点 thinking）。

#### Scenario: Cache hit without classify reasoning

- **WHEN** `/v1/analyze/intent/stream` 命中意图缓存且不执行 `classify_intent`
- **THEN** 系统 SHALL NOT 为分类节点伪造 reasoning 增量；MAY 仍推送缓存/槽位等编排字幕后返回 answer

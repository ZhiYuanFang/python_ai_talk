## ADDED Requirements

### Requirement: Temporary hardcoded runtime model in llm_client
在产品验证临时阶段，`LLMClient` 的 `_require_model_config` SHALL 返回常量硬编码的唯一 runtime 模型配置：`provider=deepseek`、`name=deepseek-v4-flash`、`max_in_flight=50`。`invoke` 与 `stream` SHALL 使用该配置发起上游调用。系统 MUST NOT 从环境变量或 settings 读取该临时型号。系统 MUST NOT 因此恢复跨 provider/name 的 fallback 换模链。

#### Scenario: invoke uses hardcoded model regardless of caller input
- **WHEN** 业务代码调用 `llm_client.invoke`，并传入与硬编码不同的 `LLMModelConfig`（例如 `provider=siliconflow`）
- **THEN** 实际上游调用 SHALL 使用 `deepseek` / `deepseek-v4-flash`，且 SHALL NOT 使用调用方传入的 provider/name

#### Scenario: stream uses hardcoded model regardless of caller input
- **WHEN** 业务代码调用 `llm_client.stream`，并传入任意合法 `LLMModelConfig`
- **THEN** 实际上游调用 SHALL 使用 `deepseek` / `deepseek-v4-flash`

#### Scenario: No env-based runtime model selection
- **WHEN** 部署环境未配置任何 `LLM_RUNTIME_*`（或等价）环境变量
- **THEN** 临时 runtime 模型选型仍 SHALL 生效（因常量硬编码于代码）

### Requirement: Observability when ignoring Go-passed model
当调用方传入的 model 的 `provider` 或 `name` 与硬编码 runtime 不一致时，系统 SHALL 以 INFO 级别记录一条日志，明确说明忽略了调用方/Go 传入的 model，并写出实际使用的 runtime provider 与 name。

#### Scenario: Log on override
- **WHEN** 传入 `provider=glm` 且硬编码为 `deepseek`/`deepseek-v4-flash`
- **THEN** 日志中 SHALL 出现可识别的「忽略」语义，并包含实际 runtime 的 provider 与 name

### Requirement: No duplicate route-level model hardcodes
意图、护理留意、成长轨迹、陪伴等 HTTP 路由 MUST NOT 再各自硬编码替换 `request.model`（或等价）作为临时选型手段；临时选型的唯一权威点 SHALL 为 `llm_client._require_model_config`。路由仍可将请求中的 `model` 写入 state/日志，但其值对实际上游选型无约束力。

#### Scenario: Route does not independently force a different model
- **WHEN** 客户端调用任意依赖 `llm_client` 的业务接口，且请求 body 含任意合法 `model`
- **THEN** 实际上游选型 SHALL 仅由 `llm_client` 硬编码决定，不得再出现路由层另一套写死型号覆盖链

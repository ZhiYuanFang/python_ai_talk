## ADDED Requirements

### Requirement: Accept zhipu as alias for glm
系统 SHALL 将 LLM provider 值 `zhipu` 与 `glm` 视为同一智谱提供商，并使用既有的 `glm_api_key` 与 `glm_base_url` 创建客户端。

#### Scenario: Provider zhipu succeeds
- **WHEN** 调用方传入 `model.provider` 为 `zhipu` 且 GLM API Key 已配置
- **THEN** 系统 SHALL NOT 因提供商名称抛出「不支持的 LLM 提供商」错误，并 SHALL 使用智谱 Base URL 发起调用

#### Scenario: Provider glm still works
- **WHEN** 调用方传入 `model.provider` 为 `glm` 且 GLM API Key 已配置
- **THEN** 系统行为与变更前一致，使用智谱配置发起调用

### Requirement: Provider name normalization
系统在选择 LLM 客户端前 SHALL 对 provider 字符串做去空白与小写规范化；`Zhipu`、`ZHIPU`、`zhipu` SHALL 等价于智谱路径。

#### Scenario: Mixed-case zhipu
- **WHEN** 调用方传入 `provider` 为 `Zhipu`
- **THEN** 系统按智谱提供商处理，不抛出不支持错误

### Requirement: Shared client cache for aliases
对同一模型名，经规范化后同属智谱的 `zhipu` 与 `glm` SHALL 共享同一客户端缓存条目。

#### Scenario: Alias hits same cache
- **WHEN** 先以 `provider=zhipu` 创建某模型客户端，再以 `provider=glm` 请求同一模型名
- **THEN** 系统复用已缓存的客户端实例（逻辑等价于同一 cache key）

### Requirement: Unknown providers still rejected
系统对既非 `deepseek`、亦非智谱别名（`glm`/`zhipu`）的 provider SHALL 继续拒绝并报错。

#### Scenario: Unsupported provider
- **WHEN** 调用方传入 `provider` 为未知值（例如 `foo`）
- **THEN** 系统抛出表示不支持该提供商的错误

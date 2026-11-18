## ADDED Requirements

### Requirement: Omitted request model uses temporary runtime

当 HTTP 请求省略 `model`（或解析结果为 None）并进入 `llm_client.invoke` / `stream` 时，`_require_model_config` MUST 仍返回临时硬编码 runtime，MUST NOT 抛出「未传入可用 model」错误，MUST NOT 读取保底换模列表。系统 SHALL 以 INFO 记录「调用方未传 model」并写出实际 runtime provider 与 name（与既有可观测约定一致）。

#### Scenario: Invoke without request model uses runtime

- **WHEN** 业务在未传 model（None）情况下调用 `llm_client.invoke`
- **THEN** 实际上游 SHALL 使用临时硬编码 runtime
- **AND** MUST NOT 因缺 model 失败于 `_require_model_config`

#### Scenario: Stream without request model uses runtime

- **WHEN** 业务在未传 model（None）情况下调用 `llm_client.stream`
- **THEN** 实际上游 SHALL 使用临时硬编码 runtime

## ADDED Requirements

### Requirement: Log full LLM request payload at INFO

`LLMClient.invoke` 与 `LLMClient.stream` 在向模型发起请求之前，MUST 以 INFO 级别记录完整发送载荷，包括模型标识、系统提示词全文（若有）以及 messages 中每条消息的 role 与 content 全文。MUST NOT 在默认路径上截断正文。

#### Scenario: Invoke logs full payload before call

- **WHEN** 调用方执行 `llm_client.invoke` 且提供 `system_prompt` 与 `messages`
- **THEN** 系统 SHALL 在模型调用前输出 INFO 日志
- **AND** 该日志 SHALL 包含 provider、model name、完整 `system_prompt`、以及每条 message 的完整 content

#### Scenario: Stream logs full payload before stream

- **WHEN** 调用方执行 `llm_client.stream` 且提供 `system_prompt` 与 `messages`
- **THEN** 系统 SHALL 在流式调用开始前输出 INFO 日志
- **AND** 该日志 SHALL 包含与 invoke 同等完整的发送载荷字段

## ADDED Requirements

### Requirement: Log LLM invoke response content at INFO

`llm_client.invoke` 在成功获得模型回复后，SHALL 以 INFO 级别记录回复正文（`content`）全文，并带有可检索的分隔标记。

#### Scenario: Invoke logs full reply text

- **WHEN** 同步调用 LLM 成功返回非空或空字符串 content
- **THEN** 日志中 SHALL 出现包含该 content 的 INFO 记录（可用 BEGIN/END 包裹）

### Requirement: Log LLM stream accumulated answer at INFO

`llm_client.stream` 在流式迭代正常结束后，SHALL 以 INFO 级别记录本轮累积的回答正文一次；SHALL NOT 为每个 chunk 单独打印完整回复日志。

#### Scenario: Stream logs answer once after completion

- **WHEN** 流式调用正常消费完毕
- **THEN** 日志中 SHALL 出现一次包含累积回答正文的 INFO 记录

#### Scenario: Thinking not required in response log

- **WHEN** `thinking_enabled=true` 且流中产生 thinking 片段
- **THEN** 响应日志 SHALL 至少包含回答正文；thinking 全文 MAY 省略

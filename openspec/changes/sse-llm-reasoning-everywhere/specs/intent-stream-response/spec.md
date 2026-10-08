## ADDED Requirements

### Requirement: Intent stream classify emits LLM reasoning

当 `/v1/analyze/intent/stream` 冷启动图路径执行 `classify_intent` 时，系统 SHALL 以 `llm_client.stream(thinking_enabled=True)` 调用分类 LLM，并将 reasoning 增量经 custom 流（或等价）以 SSE `type=thinking` 透出。分类回答正文（JSON）SHALL 聚合后再解析写入 `intent_result`；SHALL NOT 将半截 JSON 作为 `type=answer` 推送。

#### Scenario: Classify reasoning before answer

- **WHEN** 流式冷启动进入 `classify_intent` 且模型返回非空 reasoning
- **THEN** 客户端 SHALL 先收到一条或多条含 reasoning 的 `thinking` 事件，再在图完成后收到 `answer`

#### Scenario: Classify JSON not streamed as answer tokens

- **WHEN** 分类 LLM 流式产出 answer content 片段
- **THEN** 系统 SHALL 聚合 content 用于解析意图，SHALL NOT 将这些片段作为 intent SSE 的 `type=answer` 增量

### Requirement: Intent stream pending path emits LLM reasoning

当 `/v1/analyze/intent/stream` 携带有效 `conversation_id` 且进入 pending 澄清并调用澄清 LLM 时，系统 SHALL 在返回最终 `answer` 之前，将该次 LLM 的 reasoning 增量以 SSE `type=thinking` 透出。SHALL NOT 在流式 pending 路径上先 `invoke` 完成澄清再仅推送一条 `answer`（无 thinking 通道）。非流式 `/v1/analyze/intent` 的 pending 处理 MAY 继续同步 `invoke`。

#### Scenario: Pending stream shows reasoning then answer

- **WHEN** 客户端对 `/v1/analyze/intent/stream` 发送 pending 续聊且澄清 LLM 产生非空 reasoning
- **THEN** 客户端 SHALL 收到 `thinking` 增量后再收到 `answer` 与 `[DONE]`（或等价结束标记）

#### Scenario: Non-stream pending unchanged shape

- **WHEN** 客户端对非流式 `/v1/analyze/intent` 发送 pending 续聊
- **THEN** 系统 SHALL 返回完整 JSON 意图响应，且不要求 SSE thinking 事件

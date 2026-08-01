## Why

`llm_client` 已在 INFO 全量打印请求载荷（system + messages），但 `invoke` / `stream` 成功后不打印模型回复正文，排查「模型到底回了什么」只能靠业务节点零散截断日志或不完整 SSE。需在统一入口补上回复文本日志，与请求侧对称。

## What Changes

- 在 `llm_client.invoke` 成功拿到全文后，以 INFO 打印回复 `content` 全文
- 在 `llm_client.stream` 流结束后，以 INFO 打印累积的回答正文（`answer_buffer`）；不逐 chunk 打；thinking 不强制打印
- 日志带可检索分隔标记（与 request payload 风格一致）
- 无 API **BREAKING**

## Capabilities

### New Capabilities

- `llm-response-content-logging`: 同步与流式 LLM 调用成功后记录回复正文

### Modified Capabilities

- （无；延伸既有 request payload 日志约定，不改主库基线）

## Impact

- **代码**：`app/shared/llm_client.py`
- **运维**：INFO 日志量增加（与 request 同级）；所有经 llm_client 的路径自动受益

## Why

意图分类的 `system_prompt` 已包含完整事件目录（id + name），`user_message` 又重复拼一份事件名列表，浪费 token 且无信息增量。同时 `llm_client` 调用时只打 provider/model，无法在日志中核对实际发送的 system/messages，调试成本高。

## What Changes

- 删除意图分类 user 消息中的事件名列表；事件目录仅保留在 system prompt
- 同步调整 `build_intent_classification_user_message` 签名与 `classify_intent` 调用（不再传入 `event_dictionary`）
- 审计结论：其它 LLM 提示词（data_requirement / clinic / tip / history / suggest）无同类 system+user 重复目录，本次不改
- `llm_client.invoke` 与 `stream` 在真正调用前以 **INFO 全量**打印 `system_prompt` 与 `messages` 正文
- **不改动** 事件字典 24h TTL 刷新与喂养数据飞轮路径

## Capabilities

### New Capabilities

- `intent-prompt-dedupe`: 意图分类 user 消息仅含用户输入与分析指令，不重复嵌入事件目录
- `llm-request-payload-logging`: LLM 同步/流式调用前以 INFO 记录完整发送载荷（system + messages）

### Modified Capabilities

- （无：`openspec/specs/` 尚无已归档对应能力）

## Impact

- 代码：`app/feeding/graphs/nodes/prompts/intent_classification.py`、`app/feeding/graphs/nodes/classify_intent.py`、`app/shared/llm_client.py`
- 日志：INFO 将包含用户原文与可能很长的 system（含事件字典），本地调试友好；生产日志量增大
- API / 事件缓存 / 向量飞轮：无变更

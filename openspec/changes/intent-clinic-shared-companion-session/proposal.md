## Why

Intent 在 `conversation` / `suggest` 时通过 `call_clinic_agent` 同进程调用 clinic 数据准备与生成，但**不读写** tip/clinic 共享的陪伴会话（`companion:session:{device_no}`），也不走闺蜜人格提示词。用户经 tip/clinic 聊过再走 intent，或经 intent 得到建议再 clinic 续聊，上下文断裂；隐式飞轮也对 intent 建议失效。应把 intent 的陪聊路径纳入同一会话时间线（A 读 / B 写 / C 飞轮 / D 生成对齐）。

## What Changes

- **`call_clinic_agent` 读会话**：按 `device_no` 加载 companion session，注入 `chat_context`（与 tip/clinic 相同格式与轮次上限）。
- **生成前隐式飞轮**：若存在未 `feedback_applied` 的 `last_suggestion`，先做接受/拒绝/说不清三态判定并更新质量分（与 clinic stream 同逻辑；失败不阻断主流程）。
- **生成路径对齐闺蜜**：`conversation` / `suggest` 不再用 `generate_response` 的 history/suggest 旧提示词；改为与 `/clinic/stream` 一致的 `clinic_answer`（同步 invoke，非 SSE）。
- **成功后写会话**：`append_turn`（`source` 如 `intent`），更新 `last_suggestion`（全文 + 本轮注入的 knowledge ids），供后续 tip/clinic/intent 续聊与飞轮。
- **边界不变**：仅 `call_clinic_agent` 路径参与；feeding / history / pending 澄清不读写陪伴会话。HTTP 契约（intent 请求/响应字段）不强制 **BREAKING**。

## Capabilities

### New Capabilities

- `intent-companion-bridge`: Intent 经 clinic agent 时与 tip/clinic 共享陪伴会话（读写、隐式飞轮、闺蜜生成）的行为要求

### Modified Capabilities

- （无主库 `openspec/specs/` 基线；本 change 以新 capability 承载需求。逻辑上延伸既有 companion-session / implicit-feedback / bestie-persona 约定。）

## Impact

- **代码**：`app/feeding/graphs/nodes/call_clinic_agent.py`；可能复用 `companion_session`、`suggestion_acceptance`、`clinic_answer` / 同步包装；knowledge ids 抽取与 clinic 路由对齐
- **API**：`/v1/analyze/intent` 与 stream 行为增强（同会话记忆），响应形状不变
- **存储**：同一 Redis companion key；轮次截断与 TTL 沿用现配置
- **无关**：纯 feeding 落库路径、tip/clinic HTTP 主流程（仅多一方写读者）

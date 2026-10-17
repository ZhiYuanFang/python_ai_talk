## 1. 关闭思考的请求

- [x] 1.1 `llm_client` 在 `thinking_enabled=False` 且 provider 为 `aliyun_dashscope` 时，请求带 `enable_thinking: false`；LangChain 路径带不上该字段时，关闭分支改走底层客户端
- [x] 1.2 其他厂商的关闭分支仍不带 `{"thinking": {"type": "enabled"}}`

## 2. 意图调用与轮换字幕

- [x] 2.1 喂养侧全部 `stream_llm_collect` 调用传入 `thinking_enabled=False`（分类、切段、维度判定、备注、事件反查、播报策略、预测回答、澄清、漏答、日汇总）
- [x] 2.2 `stream_llm_collect` 在关闭思考时，调用开始立即推送 `\r努力思考中`，之后每 1 秒与 `\r正在思考中` 轮换；调用结束或失败时取消；不转发模型 reasoning
- [x] 2.3 `thinking_enabled=True` 的路径（诊所判定、成长轨迹、留意点）仍走原有 reasoning 透出；`stream_response` 不改

## 3. 约定文案

- [x] 3.1 更新 `openspec/project.md` 与 `AGENTS.md`：意图链路 SSE LLM 使用 `thinking_enabled=False`，对外 thinking 为上述两句轮换；其余对外 SSE LLM 仍开启 thinking 并透出 reasoning

## 4. 手工验收

- [ ] 4.1 意图流式请求的日志里，喂养 LLM 的 `thinking_enabled=false`，通义请求含 `enable_thinking: false`；字幕在「努力思考中」与「正在思考中」之间按秒切换，看不到模型思考原文
- [ ] 4.2 诊所流式回答仍能看到模型 reasoning，节点固定字幕文案未被改成这两句

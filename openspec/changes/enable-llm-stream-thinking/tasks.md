## 1. LLM native stream thinking

- [x] 1.1 在 `llm_client.stream` 于 `thinking_enabled=True` 时为 deepseek/glm 请求启用原生 thinking（调用时覆盖，不永久污染缓存客户端）
- [x] 1.2 实现从流式 chunk 提取 `reasoning_content`（及等价路径）→ `LLMResponse.thinking`，`content` → 正文；同 chunk 可并存
- [x] 1.3 移除或降级以 `[思考]` / `思考：` 解析正文作为 thinking 主路径

## 2. Thinking newline rules

- [x] 2.1 `emit_thinking`（及必要时共享小工具）保证编排 thinking 末尾有 `\n`（已有则不重复追加）
- [x] 2.2 确认 clinic/tip 路由中编排字幕（如 `llm_start`）同样末尾 `\n`；LLM `chunk.thinking` 转发不加 `\n`

## 3. Tests and smoke

- [x] 3.1 单测：mock chunk 带 reasoning/content，断言 `LLMResponse` 映射与「LLM thinking 不加尾部换行」
- [x] 3.2 单测：`emit_thinking` / 编排出口末尾 `\n` 行为
- [x] 3.3 手工或现有路径冒烟：clinic/tip 流式在支持思考的模型上 SSE 出现非空 LLM thinking，编排字幕仍分段正常

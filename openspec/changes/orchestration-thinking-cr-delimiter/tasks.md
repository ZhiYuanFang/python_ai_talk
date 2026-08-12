## 1. Helper 与注释

- [x] 1.1 将 `ensure_orchestration_thinking_content` 尾部分隔符从 `\n` 改为 `\r`（幂等只认 `\r`；已以 `\n` 结尾时仍追加 `\r`）
- [x] 1.2 更新该函数与 `emit_thinking` 的中文注释，标明编排条目分隔为 CR、LLM 路径不得调用

## 2. 调用点核对

- [x] 2.1 确认 clinic/tip 路由层 `llm_start` 等编排字幕仍只经该 helper，无旁路硬编码 `\n`
- [x] 2.2 确认 LLM 流式 thinking 转发路径不调用该 helper、不加尾部 `\r`

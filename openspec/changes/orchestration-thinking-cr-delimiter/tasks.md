## 1. Helper：段首 \r

- [x] 1.1 将 `ensure_orchestration_thinking_content` 改为非空且不以 `\r` 开头时前置 `\r`（幂等 `startswith`）
- [x] 1.2 更新 helper 与 `emit_thinking` 中文注释（段首开泡；可供 LLM 首包复用）

## 2. 路由：LLM 首包开泡

- [x] 2.1 clinic 流式：首次非空 `chunk.thinking` 经 helper 保证段首 `\r`，其后原样转发
- [x] 2.2 tip 流式：同上

## 3. 编排调用点

- [x] 3.1 确认 `emit_thinking` / `llm_start` 仍走 helper，无旁路硬编码尾部 `\r` 或 `\n`

## Why

客户端将多条编排阶段 thinking 字幕拼成 buffer 后按分隔符切「条目」。当前尾部分隔符是 `\n`，与 LLM 思考正文里的换行冲突，易误切。改用 `\r` 作为条目边界，与客户端同步切换，可把「条目分隔」与「行内换行」拆开。

## What Changes

- **BREAKING**：编排阶段 thinking 字幕（`emit_thinking`、路由层 `llm_start` 等）尾部分隔符由 `\n` 改为 `\r`；非空且不以 `\r` 结尾时追加 `\r`。
- 幂等规则只认 `\r`：若文案已以 `\n` 结尾但不以 `\r` 结尾，仍追加 `\r`（可能得到 `…\n\r`），不剥离既有 `\n`。
- LLM 流式 thinking 增量仍原样转发，不追加 `\r` 或 `\n` 作为条目分隔。
- 更新 `llm-native-stream-thinking` 中「编排 thinking 尾部换行」相关 Requirement / Scenario。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `llm-native-stream-thinking`：编排 thinking 尾部分隔符从 LF (`\n`) 改为 CR (`\r`)；LLM 增量仍不加强制尾部分隔符（表述与编排要求对齐）。

## Impact

- 代码：`app/shared/graphs/node_thinking.py` 的 `ensure_orchestration_thinking_content`；`clinic`/`tip` 路由已复用该 helper，行为随 helper 变更。
- API：SSE `thinking` 事件中编排字幕 `content` 尾字符变化（**BREAKING**，客户端须同步 `split('\r')`）。
- 测试：不生成、不修改测试文件（仓库不使用测试）。

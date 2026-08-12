## Why

客户端按「段首 `\r` = 新气泡、否则追加」解析 thinking SSE。编排字幕与 LLM 思考段均需在段首带 `\r` 开新气泡；正文内 `\n` 仅作行内换行。相对曾用的尾部 `\r`/`\n`，段首标记更贴合流式开泡语义。

## What Changes

- **BREAKING**：编排阶段 thinking（`emit_thinking`、`llm_start` 等）由尾部 `\r` 改为**段首** `\r`；非空且不以 `\r` 开头时前置 `\r`。
- **BREAKING**：clinic/tip 路由在**首次**非空 LLM `thinking` 增量前同样保证段首 `\r`；后续 thinking 增量原样转发，不再加 `\r`。
- 幂等只认段首 `\r`（`startswith`）；不剥离正文中的 `\n`。
- 更新 `llm-native-stream-thinking` 相关 Requirement / Scenario。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `llm-native-stream-thinking`：编排 thinking 与 LLM 思考「段」以段首 `\r` 开泡；LLM 仅首包加前缀，后续增量不加。

## Impact

- 代码：`ensure_orchestration_thinking_content`（段首）；`clinic`/`tip` 路由对首次 `chunk.thinking` 调用同一 helper。
- API：SSE thinking `content` 段首字符约定（**BREAKING**，客户端已约定段首 `\r` = 新气泡）。
- 不生成、不修改测试文件。

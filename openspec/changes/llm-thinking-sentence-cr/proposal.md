## Why

LLM reasoning 流式增量会连成一大段 thinking，客户端按「段首 `\r` = 清空/新开展示」解析时，长篇思考挤在同一泡里难读。需要在**不改编排字幕与既有首包开泡逻辑**的前提下，按句界在「下一句开头」插入 `\r`，让界面只保留短文案；句末不得贴 `\r`，否则最后一句会被清空。

## What Changes

- 所有 agent 对外 SSE 路径上的 **LLM thinking 流**增加句界检测：句界为中文 `。！？` 与英文 `.!?`。
- 判定上一句已在句界结束之后，**下一句输出的开头**前置 `\r`；**禁止**在句界字符后直接拼接 `\r`（避免流结束时空字幕）。
- **不改**编排 `emit_thinking` 段首 `\r`、clinic/pending「首包开泡」等既有逻辑；本能力叠加在 LLM reasoning 出口。
- 收窄并补充既有「LLM 后续增量不得加 `\r`」：允许且仅允许「上句已结束后的下一句开头」加 `\r`。

## Capabilities

### New Capabilities

- `llm-thinking-sentence-cr`：流式 LLM reasoning 按句在下一句首加 `\r`；句末不加；覆盖全部 agent

### Modified Capabilities

- `llm-native-stream-thinking`：允许句级下一句首 `\r`；明确禁止句末贴 `\r`；编排逻辑不变

## Impact

- Python shared：thinking 句缓冲 rewriter；`stream_llm_collect`；凡直接转发 `chunk.thinking` 的路由（如 clinic 主答）须走同一 helper
- feeding / clinic / care-alert / growth-trajectory：凡 SSE LLM reasoning 出口
- 客户端：沿用段首 `\r` 清空/换显；无需新协议字段

## Why

段多维在 EVENT 已能把「睡醒了」对齐到计时叶「睡眠」，但 SHAPE 仅由 `op`+`event_type` 推导：`time`+`create` 一律 `action=start`。TYPE 结束词表不含「醒了/睡醒」，于是确认成「现在开始睡眠」而非结束。形态维需要规则线索 + 窄契约小 LLM 兜底，裁定计时开表/结束/补记。

## What Changes

- SHAPE 维：规则结束线索扩写（如醒了/睡醒/起床）→ 仍暧昧时对 **type=time** 叶调用 SHAPE 小 LLM。
- 小 LLM 可回写 `op`/`action`（`create+start` / `end+end` / `create+one`），MUST NOT 改 `event_id`。
- 提示词落 `prompts/system.py`；SSE 真流式 + 中文 reasoning；调用写 `rule_gap(dimension=shape, llm_used=true)`。
- MUST NOT 恢复满血 classify；one/number 叶仍以现有推导为主（可不调 SHAPE LLM）。

## Capabilities

### New Capabilities

- `intent-shape-llm-fallback`：计时形态（start/end/补记 one）规则线索与小 LLM 触发、契约、缺口

### Modified Capabilities

- `intent-segment-multidim`：SHAPE 由纯推导改为规则 + 可选小 LLM；段序仍 TYPE→EVENT→REMARK→SHAPE→QTY→TIME
- `intent-dim-llm-fallback`：撤销「SHAPE 不要 LLM」的隐含非目标，与五维兜底对齐（相对未收版 change 的衔接）
- `intent-rule-gap-inbox`：形态维走 LLM 时 MUST `llm_used=true`

## Impact

- **Python**：`segment_multidim.resolve_shape`（或 async 包装）、`segment_dim_llm` 增加 SHAPE、`prompts/system.py`、确认话术随 `op=end` 走既有「现在结束」模板。
- **依赖**：叠在段多维 + EVENT 小 LLM（`intent-dim-llm-fallback`）之上。

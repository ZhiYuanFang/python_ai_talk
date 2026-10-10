## Why

段多维主路径摘掉备注反查后，「AD」「菠菜」等字典外/实例词无法定事件；同时「尿尿了，这次有点黄」类自由明细没有写入 `remark` 的通道。需要在段流水线补齐：用已有字典 `extra_names` 做类别实例别名（Hub 已能改字典，不新建别名表）、事件 miss 后 Go 备注反查，以及全事件可带的 LLM 明细备注。

## What Changes

- 段 EVENT 维顺序：**词典名 → `extra_names` 精确命中（`remark`=该别名）→ 短说法向量 → Go 备注模糊反查 → miss/重说**。
- **`extra_names` 语义扩展**：除近义外，亦表示「属于该事件的实例词」（如辅食←菠菜）；命中时事件用字典正式名，明细写入 `remark`。
- **不新建**类别别名表、**不新增** Hub 别名 CRUD（沿用事件字典 `extraNames` 编辑）。
- 任意事件允许明细备注；自由描述（如「有点黄」）**MUST** 由专用小 LLM 从段原文抽取（可空），MUST NOT 用规则硬截。
- 复用既有 Go `remark` filter 与 `resolve_remark_event` 聚合/消歧逻辑，挂入段多维而非复活满血 classify。

## Capabilities

### New Capabilities

- `intent-segment-remark`：段级备注——extra_names 别名、miss 后 Go 反查、全事件 LLM 明细抽取与落库/确认带出

### Modified Capabilities

- `intent-segment-multidim`：EVENT 维扩展上述阶梯；流水线增加 REMARK（LLM）步（相对未收版 change 的增量约定）
- `history-remark-filter`：明确段 miss 路径复用同一 Go 备注模糊（若基线无独立 capability，则仅在新能力 Scenario 中引用行为）

## Impact

- **Python**：`segment_multidim` / `resolve_segments`、`event_name_match` 或等价 extra_names 扫描、异步备注反查、明细 LLM 提示（`prompts/system.py`）、确认话术带 remark、batch 已支持的 `remark` 字段写满。
- **Go**：无新表/新 Hub 页；字典 `extraNames` 维护照旧；filter 备注能力照旧。
- **依赖**：宜在 `intent-segment-multidim` 段多维主路径之上实现（可同仓并行，以多维图为准）。

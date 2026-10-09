## Why

意图分类路径上，LLM 常在 reasoning 里逐步推算钟点/Unix，提示里手算细则又长，导致「时间相关」体感耗时长。本仓已有规则抽取（`extract_clocks` / duration / `apply_time_slots`），却几乎只在缓存 overlay 与落库前使用。应在分类前注入预解析、瘦身时间手算提示，并在确认前用同一套规则盖时间，使确认与落库一致并减少模型时间推理。

## What Changes

- 分类前用现有规则抽取 clocks / duration（及半命中标记），以短块注入 classify system 的 `{extra}`（与进行中计时并列），供模型优先参考。
- 瘦身 `INTENT_CLASSIFICATION_SYSTEM_TEMPLATE` 中教模型自行换算日段/「N分钟→unix」的长文；改为：有预解析则采用其 unix，reasoning 禁止逐步推算 Unix；保留字段语义、开表/闭合、`ignore_time_range`、多事件等必要约束。
- **策略 C**：时间权威在确认前对 CUD `events[]` 调用 `apply_time_slots_to_events`（与落库前同规则），再生成 leaf_confirm 话术；注入为软提示，不锁死 JSON。
- 半命中（partial）时注入标明不完整；确认前 apply 跳过残缺 clock（沿用既有半命中行为）。
- **不改**缓存命中 overlay 主路径；**不关** `thinking_enabled`。

## Capabilities

### New Capabilities

- （无）

### Modified Capabilities

- `intent-analysis`: 分类前预解析时间注入 + 时间手算提示瘦身；reasoning 勿逐步推 Unix
- `feeding-intent-user-confirmation`: 确认前规则盖时间后再出确认话术，与落库时间一致

## Impact

- **本仓**：`intent_classification` 提示构建、`classify_intent`、`INTENT_CLASSIFICATION_SYSTEM_TEMPLATE`、`intent_pipeline.postprocess`（确认前 apply）；复用 `time_slot_extractor` / `closed_interval`。
- **API / 兄弟仓**：无接口变更。
- **缓存路径**：明确不在范围。

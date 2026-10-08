## Why

用户说「昨晚6点洗澡了」时期望落在**昨天 18:00**，但规则只吃到「6点」、忽略「昨晚」，落成**今天早上 6:00** 并免确认落库。半命中比完全抽不到更危险：错误时间被当真。需要补齐常见日段词，并在「抽到 clock 仍有未消费时间残留」时取消免确认、改走 LLM 分析。

## What Changes

- 钟点前缀识别「昨晚 / 昨夜」等：日偏移为昨天，并把 1–11 点按晚上口语抬到 12–23（如「昨晚6点」→ 昨日 18:00）。
- **半命中降级**：当规则已抽到至少 1 个 clock，但原文去掉已匹配 span 后仍含未消费的日/段时间词时，MUST NOT 用规则时间免确认落库；overlay 取消缓存命中，走 classify LLM。
- 落库前 `apply_time_slots_to_events` 在同样半命中时 MUST NOT 用残缺 clock 覆盖（避免分类路径再被错误规则踩掉 LLM 时间）。
- **不**在「无 clock、仅有日段词」或「无任何时间残留」时因本条强制降级（用户选定：仅当抽到 clock 且仍有残留）。

## Capabilities

### New Capabilities

- （无）行为落在既有槽位覆盖能力上。

### Modified Capabilities

- `intent-slot-overlay`: 「昨晚」等日段合法解析；半命中（有 clock + 未消费时间残留）强制降级 LLM，且禁止残缺 clock 覆盖落库时间

## Impact

- **本仓**：`time_slot_extractor`、`closed_interval`（残留判定 / degrade）、`overlay_slots`；`execute_history_crud` 经共用 apply 间接受益。
- **API / 兄弟仓**：无接口变更。
- **关联**：与 `intent-timer-closed-interval` 多钟点降级并存；半命中为独立降级条件。

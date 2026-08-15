## ADDED Requirements

### Requirement: 分类输出 ignore_time_range 并由 LLM 判定上一次

意图分类结果中，每个 `events[]` 子项 SHALL 可包含布尔字段 `ignore_time_range`（缺省 false）。当 `op=read` 且用户语义为「上一次 / 上次 / 最近一次」等不依赖具体日历区间的点查时，分类模型 MUST 将该子项 `ignore_time_range` 设为 true；当用户给出明确日期、今天/昨天/本周等区间或汇总范围时，MUST 设为 false（或不写）并填写对应 unix 时间窗。分类提示词 MUST 说明该字段含义与极性。`IntentEventItem`（或等价 schema）MUST 保留该字段，MUST NOT 因 `extra=ignore` 丢弃模型输出。

#### Scenario: 上一次语义输出 true

- **WHEN** 用户输入「上一次睡觉是什么时候」且分类成功
- **THEN** 对应 `op=read` 子项的 `ignore_time_range` MUST 为 true

#### Scenario: 今天语义输出 false 并带窗

- **WHEN** 用户输入「今天拉了几次」且分类成功
- **THEN** 对应 `op=read` 子项的 `ignore_time_range` MUST 为 false 或缺省
- **AND** 该子项 MUST 带有表示「今天」的 unix `start_time`/`end_time`

## ADDED Requirements

### Requirement: 多事件确认须点出时间与数量
当 `events` 长度大于 1 且需要用户确认时，`confirm_message` SHALL 逐项点出事件名，并在该子项存在数量或钟点时应一并读出（不得仅重复事件名而无量、无时）。系统 MUST NOT 使用只含「记录 A、记录 A 并记录 B」且完全省略毫升与钟点的文案作为多时刻喂养的唯一确认语。

#### Scenario: 三条喂养确认含量时
- **WHEN** 分类得到三条 create（含配方奶两次与母乳一次）且带数量与 start_time
- **AND** 需要确认
- **THEN** `confirm_message` SHALL 能区分三条，并体现各自数量与时间信息（或等价可读表述）

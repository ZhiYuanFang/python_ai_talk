## ADDED Requirements

### Requirement: Predict SHALL carry a separate ask aspect

When `read_source` is `predict`, the intent result MUST include `predict_aspect` of `when`, `amount`, or `duration`, stored separately from `predict_channel` and `time_answer`. `time_answer` MUST be `clock` or `remain` only when `predict_aspect` is `when`. When `predict_aspect` is `amount` or `duration`, `time_answer` MUST be empty. `predict_channel` MUST still be `active` or `next`. Utterances about the last completed record (上次 / 上一次, including how much was eaten or how long it lasted) MUST remain `read` with `read_source=record` and MUST NOT be classified as predict amount or duration.

预测问法 MUST 用独立的 `predict_aspect`（何时 / 用量 / 用时）。用量与用时不得占用 `time_answer`。上次吃了多少、上次用时 MUST 仍是查记录。

#### Scenario: Upcoming formula amount

- **WHEN** 用户说「这次配方奶要吃多少」且事件能对齐到配方奶
- **THEN** `read_source` MUST 为 `predict`，`predict_channel` MUST 为 `next`，`predict_aspect` MUST 为 `amount`，`time_answer` MUST 为空

#### Scenario: Upcoming duration

- **WHEN** 用户问即将发生的这一次大概要持续多久（如「这次要睡多久」）且已判为预测
- **THEN** `predict_aspect` MUST 为 `duration`，`time_answer` MUST 为空

#### Scenario: When-question keeps clock or remain

- **WHEN** 用户问下一次几点或还有多久，且已判为预测
- **THEN** `predict_aspect` MUST 为 `when`，`time_answer` MUST 为 `clock` 或 `remain`

#### Scenario: Last record stays history

- **WHEN** 用户问「上次吃了多少」或「睡了多久」这类已发生记录
- **THEN** `read_source` MUST 为 `record`，MUST NOT 写成预测用量或预测用时

### Requirement: Unsure predict confirm SHALL follow the ask aspect

When a predict turn sets `need_confirm` and does not execute, the confirm sentence MUST follow `predict_aspect`: amount asks whether the user wants the expected amount, duration asks whether the user wants how long it will last, `when`+`remain` asks how much longer, and `when`+`clock` asks about the clock time. The confirm sentence MUST NOT ask「大概还要多久」for an amount or duration aspect. A predict turn with an illegal or empty aspect MUST set `need_confirm` and MUST NOT execute. Flywheel write MUST stay off while `need_confirm` is true.

预测没把握时的确认句 MUST 跟着用量 / 用时 / 何时走，用量题不得追问还要多久。

#### Scenario: Amount confirm

- **WHEN** 预测轨 `predict_aspect=amount` 且 `need_confirm` 为真
- **THEN** 确认句 MUST 体现「要多少」，MUST NOT 问「大概还要多久」

#### Scenario: Duration confirm

- **WHEN** 预测轨 `predict_aspect=duration` 且 `need_confirm` 为真
- **THEN** 确认句 MUST 体现「大概要持续多久」，MUST NOT 问成距离开始还有多久

### Requirement: Legacy predict cues without aspect SHALL read as when

When a predict flywheel hit has no `predict_aspect`, the system MUST treat it as `when` and MUST keep the stored `predict_channel` and `time_answer`. New flywheel writes for a confident predict turn MUST store `predict_aspect` together with the channel and, when aspect is `when`, the time answer.

没有 `predict_aspect` 的旧预测飞轮 MUST 按何时读取。

#### Scenario: Old cue

- **WHEN** 预测飞轮命中一条没有 `predict_aspect` 的载荷，且 channel 与 time_answer 合法
- **THEN** 系统 MUST 按 `predict_aspect=when` 继续，MUST NOT 改判成用量或用时

### Requirement: Algorithm snapshot SHALL keep both amount and duration

When the local prediction tool has enough samples for expected amount and expected duration, the tool result MUST include both values. The speaker MUST use only the value selected by `predict_aspect`. If the selected value is missing, the reply MUST say that value cannot be estimated and MUST NOT substitute the other value or a last-record duration sentence.

样本够时预计用量和预计用时 MUST 都留下。问哪一格就只念哪一个数。

#### Scenario: Both metrics present

- **WHEN** 冷路径样本同时够用量和用时，且本轮 `predict_aspect=amount`
- **THEN** 工具结果 MUST 仍带预计用时，对外回答 MUST 依据预计用量，MUST NOT 改念用时

#### Scenario: Asked metric missing

- **WHEN** `predict_aspect=amount` 但预计用量不可用
- **THEN** 回答 MUST 说明用量估不出，MUST NOT 改念预计用时或「上一次用时」

## ADDED Requirements

### Requirement: Missing event id SHALL guess from window history without asking

When a read-record speak path has no event id, the system MUST NOT ask the user which event to query. It MUST load history for the already resolved time window across events. When the turn is a point query, or the window is empty under an ignore-time point query, it MUST load a point-style recent slice across events and MUST NOT fetch an unbounded full history. An LLM MUST answer in no more than 20 Chinese characters using only that history. The system MUST NOT write an event-phrase flywheel entry for this guess. The system MUST record a rule gap in a missing-event dimension.

#### Scenario: No event id uses short LLM answer

- **WHEN** 查史播报没有事件编号且已有时间窗或点查最近范围
- **THEN** 系统 MUST NOT 回复请先说明要查哪个事件
- **AND** 用户回答 MUST 不超过二十个字
- **AND** MUST 记规则缺口且不写事件说法飞轮

### Requirement: Clarification and empty rows SHALL stay unchanged

Parent or leaf disambiguation and soft confirmation MUST still ask the user. Segment failure that cannot align an event name MUST still use the existing unresolved-event miss path. When an event id exists but that event has no rows, the system MUST keep the no-record answer and MUST NOT switch to the all-events guess.

#### Scenario: Disambiguation still asks

- **WHEN** 一句话对上多个事件需要消歧
- **THEN** 系统 MUST 仍向用户确认是哪一个
- **AND** MUST NOT 改走无事件编号的二十字猜测

#### Scenario: Known event with no rows

- **WHEN** 事件编号已对齐但该事件在窗内没有记录
- **THEN** 系统 SHALL 表示没有相关记录
- **AND** MUST NOT 改拉全部事件再猜测

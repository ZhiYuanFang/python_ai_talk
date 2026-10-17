## ADDED Requirements

### Requirement: Point-query speak policy uses local rules before the flywheel

点查播报在查询飞轮或调用播报模型之前 MUST 先匹配本地规则。句中含「上次」「上一次」或「最近一次」时，系统 MUST 采用 `prefer_completed` 与 `in_progress`。不含这些词但含「多久了」或「多长时间了」时，系统 MUST 采用 `latest` 与 `elapsed`。规则命中时系统 MUST NOT 查询播报飞轮，也 MUST NOT 调用播报模型。规则未命中时 MUST 保持先飞轮、再模型的顺序。

#### Scenario: Last feeding time skips the speak model

- **WHEN** 用户说「上一次配方奶是什么时候」且本轮已是点查
- **THEN** 播报策略 MUST 为优先已完成、进行中只说正在进行
- **AND** MUST NOT 调用查史点查播报策略模型

#### Scenario: Elapsed duration stays on the latest row

- **WHEN** 用户说「睡了多久了」且本轮已是点查
- **THEN** 播报策略 MUST 为最近一条、进行中报已持续多久
- **AND** MUST NOT 判成优先已完成

#### Scenario: Prior session duration is not an elapsed query

- **WHEN** 用户说「上次睡眠多久」且本轮已是点查
- **THEN** 播报策略 MUST 为优先已完成、进行中只说正在进行

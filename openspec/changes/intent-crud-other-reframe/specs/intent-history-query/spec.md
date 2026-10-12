## ADDED Requirements

### Requirement: 查史点查收归 read·record
点查/日汇总类查史 MUST 在顶层意图轨为 `read` 且 R 内 `source=record` 时执行。选行与进行中话术 SHALL 服从整段查史播报飞轮（或等价 R·record 播报层），MUST NOT 依赖已废除的顶层 `history` target_type 作为唯一入口。

#### Scenario: 睡了多久了走 read record
- **WHEN** 用户说「睡了多久了」且判为 read + source=record
- **THEN** 系统 SHALL 走查史拉数与 record 播报策略
- **AND** MUST NOT 要求顶层 target_type=history

## ADDED Requirements

### Requirement: 不得再提供 feeding_events 标准向量重建开关
因 `feeding_events` 已拆除，系统 MUST NOT 再实现或配置 `REBUILD_FEEDING_STANDARD_EVENTS`。运维清空意图缓存 MUST 使用 `CLEAR_FEEDING_INTENTS_ON_STARTUP`，且仅作用于 `feeding_intents`。

#### Scenario: Startup does not rebuild feeding_events standard rows
- **WHEN** 服务启动
- **THEN** 系统 SHALL NOT 读取或执行 `REBUILD_FEEDING_STANDARD_EVENTS`
- **AND** SHALL NOT 因任何启动开关重建 `feeding_events` 的 source=standard 条目

## REMOVED Requirements

### Requirement: 系统在用户确认LLM解析意图后添加用户表达
**Reason**: 单事件用户表达飞轮会把复合句绑到一个 `event_id`，与多事件 CRUD 意图缓存冲突。
**Migration**: 确认成功后写入 `intent-cache-flywheel` 所定义的意图缓存；停止调用 `add_user_expression`。

### Requirement: 系统设置向量库最大记录数
**Reason**: 该容量与清理规则针对 `feeding_events` 用户表达；本变更不再写入该类记录。
**Migration**: 意图缓存若需容量治理，在 `intent-cache-flywheel` 实现中单独约定，不沿用本条对用户表达 20% 删除。

### Requirement: 系统计算向量数据质量评分
**Reason**: 质量分用于清理单事件用户表达。
**Migration**: 不再对 `source=user` 喂养表达计分清理。

### Requirement: 系统记录向量数据的匹配计数和成功计数
**Reason**: `match_count`/`success_count` 服务于单事件飞轮。
**Migration**: 意图缓存可自有命中统计；不得再对单事件用户向量 `increment_success_count` 作为主飞轮。

## ADDED Requirements

### Requirement: 停止单事件用户表达飞轮
系统 MUST 删除单事件用户表达飞轮相关代码（含 `add_user_expression`、用户表达的匹配/成功计数递增、针对用户表达的清理，以及确认路径上的飞轮写入）。系统 MUST NOT 再将用户原话作为 `feeding_events` 中 `source=user` 的单事件表达写入。存量用户表达 MUST NOT 再用于意图快路径检索（排除或删除）。知识库 `source=user` MUST NOT 随本条删除。

#### Scenario: 确认后不写 user 表达
- **WHEN** 用户确认喂养意图正确并落库成功
- **THEN** 系统 SHALL NOT 调用 `add_user_expression`（该 API 应已删除或无引用）
- **AND** SHALL 按意图缓存能力写入整份意图（若该次允许缓存）

## ADDED Requirements

### Requirement: 意图图按子项 op 与 target_type 路由
意图图在意图就绪且无需继续备注反查后，SHALL 按下列规则路由：若 `need_confirm` 则结束等待确认；若存在子项 `op=read` 或 `target_type=history` 则进入模板查记录；若存在子项 `op` 属于 `create|update|delete|end` 则进入批量落库；若 `target_type` 为 `conversation` 或 `exit` 则结束。路由 MUST NOT 读取顶层 `op` 或顶层 `action`。

#### Scenario: 已确认复合 CUD
- **WHEN** `need_confirm` 为假且 `events` 含 `end` 与 `create`
- **THEN** 图 SHALL 进入批量落库节点

#### Scenario: 查记录
- **WHEN** `events` 含 `op=read`（或 `target_type=history`）且不需确认或已确认
- **THEN** 图 SHALL 进入查记录播报节点

#### Scenario: 闲聊
- **WHEN** `target_type` 为 `conversation` 且无 CUD/read 子项
- **THEN** 图 SHALL 结束且不进入批量落库

### Requirement: 意图缓存载荷以 events 为准
意图缓存写入与命中复用时，载荷 MUST 包含 `events`（每项含 `op`），MUST NOT 依赖顶层 `op` 作为唯一操作权威。旧缓存若仅有顶层 `op` 而无可用 `events`，系统 MUST 视为不可复用或先投影为 `events` 后再用。

#### Scenario: 缓存命中复合意图
- **WHEN** 缓存载荷含带 `op` 的 `events` 且相似度达标
- **THEN** 系统 SHALL 能按子项 `op` 路由执行或确认
- **AND** MUST NOT 因缺少顶层 `op` 而拒绝命中

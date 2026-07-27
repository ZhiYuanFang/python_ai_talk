## ADDED Requirements

### Requirement: Full tree and leaf view separation

系统 MUST 在事件字典缓存中保留全量事件树，并派生仅含叶子事件的视图。父事件定义为：其 `event_id` 出现在任一事件的非空 `parent_id` 集合中。对外用于匹配候选与最终落库的事件集合 MUST 为叶子视图。

#### Scenario: Leaves exclude parents with children

- **WHEN** 事件字典中存在事件 A，且至少另一事件的 `parent_id` 等于 A 的 `event_id`
- **THEN** 叶子视图 MUST NOT 包含 A
- **AND** 叶子视图 MUST 包含指向 A 的子事件（若该子事件自身不再是其他事件的父）

#### Scenario: Events without children remain selectable

- **WHEN** 某事件的 `event_id` 不出现在任何非空 `parent_id` 中
- **THEN** 该事件 MUST 出现在叶子视图中并允许作为落库目标

### Requirement: Twenty-four hour dictionary refresh preserves invariants

事件字典 MUST 继续按配置 TTL（默认 24 小时）从兄弟仓刷新。刷新后 MUST 重新派生叶子视图，并按现有增量同步机制更新向量库标准条目，且 MUST 保持「父不可落库、用户表达保留」的不变量。

#### Scenario: TTL expiry refetches and resyncs

- **WHEN** 事件字典缓存已过期
- **AND** 业务路径再次请求事件字典
- **THEN** 系统 SHALL 从兄弟仓重新获取全量事件字典
- **AND** SHALL 派生新的叶子视图
- **AND** SHALL 触发与缓存更新绑定的向量同步逻辑

#### Scenario: Standard sync does not delete user flywheel expressions

- **WHEN** 事件字典刷新触发标准事件同步或父事件移除
- **THEN** 系统 MUST NOT 删除 `source=user` 的用户表达记录
- **AND** MUST NOT 将父事件作为可落库的标准最终事件保留

## ADDED Requirements

### Requirement: Vector match node reuses module singleton

喂养意图向量匹配节点 MUST 使用模块级单例 `event_vector_store` 执行检索，MUST NOT 在每次节点调用时构造新的 `EventVectorStore` 实例。

#### Scenario: Match uses shared singleton

- **WHEN** 意图图执行 `match_event_by_vector` 且用户输入非空
- **THEN** 节点 SHALL 调用模块级 `event_vector_store.search_events`（或等价公开方法）
- **AND** SHALL NOT 执行 `EventVectorStore()` 以创建新实例

#### Scenario: Embedding and Chroma initialize once per process instance

- **WHEN** 同一进程内模块级 `event_vector_store` 已完成 `_ensure_initialized`
- **AND** 后续请求再次进入向量匹配
- **THEN** 系统 SHALL NOT 再次加载 Embedding 模型或重建 Chroma PersistentClient
- **AND** SHALL NOT 再次打印「喂养事件向量存储初始化完成」

### Requirement: Event dictionary 24-hour refresh unchanged

事件字典缓存的 24 小时（或 `event_cache_ttl_hours` 配置）刷新行为 MUST 保持不变；本变更 MUST NOT 修改 TTL、缓存命中逻辑或缓存更新时的向量同步触发条件。

#### Scenario: Cache hit within TTL

- **WHEN** 事件字典已缓存且未超过 TTL
- **AND** 业务路径请求事件字典
- **THEN** 系统 SHALL 返回缓存数据且 SHALL NOT 调用兄弟仓事件字典接口

#### Scenario: Cache miss after TTL triggers API and sync

- **WHEN** 事件字典缓存已过期（或未命中）
- **AND** 业务路径请求事件字典
- **THEN** 系统 SHALL 从兄弟仓重新获取事件字典
- **AND** SHALL 按现有逻辑调用 `_sync_vector_store_if_changed`（首次 `initialize_events`，其后差分 `sync_events`）

### Requirement: Feeding data flywheel remains effective

数据飞轮写入 MUST 继续写入与向量匹配相同的 `feeding_events` 集合；用户表达（`source=user`）MUST NOT 被标准事件同步清空。匹配与飞轮 MUST 共享同一模块级向量存储实例。

#### Scenario: Confirm after LLM match adds user expression

- **WHEN** 用户确认意图且 `match_source` 为 `llm`
- **THEN** 系统 SHALL 通过模块级 `event_vector_store.add_user_expression` 将用户表达写入向量库（`source=user`）

#### Scenario: Confirm after vector match increments success count

- **WHEN** 用户确认意图且 `match_source` 为 `vector` 且存在 `matched_vector_id`
- **THEN** 系统 SHALL 对该向量 ID 递增 `success_count`

#### Scenario: Standard sync preserves user expressions

- **WHEN** 事件字典刷新触发 `initialize_events` 或 `sync_events`
- **THEN** 系统 SHALL 仅变更 `source=standard` 的记录
- **AND** SHALL 保留已有 `source=user` 的用户表达记录

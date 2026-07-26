## ADDED Requirements

### Requirement: 使用 search_events 检索
`match_event_by_vector` SHALL 调用 `EventVectorStore.search_events`（或经该实现的等价公开方法），不得调用不存在的 `search` 方法。

#### Scenario: 向量匹配不再 AttributeError
- **WHEN** 用户输入非空且事件向量库已初始化
- **THEN** 向量匹配节点 SHALL NOT 抛出 `'EventVectorStore' object has no attribute 'search'`
- **AND** SHALL 使用 `search_events` 的返回列表继续置信度分支

### Requirement: 使用 score 作为置信度
向量匹配置信度 SHALL 基于 `search_events` 返回的 `score` 字段（0–1 相似度），不得假定存在 Milvus 风格的 `distance` 键并对其做错误的 L2 归一化。

#### Scenario: 高/中置信分支可读 score
- **WHEN** `search_events` 返回至少一条含 `score` 与 `metadata` 的结果
- **THEN** 节点 SHALL 用该 `score` 与现有高/中置信阈值比较并路由

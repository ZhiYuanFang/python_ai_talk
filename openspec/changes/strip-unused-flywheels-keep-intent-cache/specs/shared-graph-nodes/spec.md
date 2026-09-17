## ADDED Requirements

### Requirement: Clinic and tip MUST NOT inject general knowledge retrieval

clinic 与 tip 图路径 MUST NOT 调用通识向量检索（原 `search_vectors` / `mother_baby_knowledge`）并向回答 prompt 注入「知识库参考」类摘录。共享节点目录中若仍保留 `search_vectors` 实现，MUST NOT 被 clinic/tip 图挂载。

#### Scenario: Tip graph has no search_vectors edge

- **WHEN** 构建 tip_graph
- **THEN** 节点序列 MUST NOT 包含通向通识检索的边

#### Scenario: Clinic graph has no knowledge injection node

- **WHEN** 构建 clinic_graph
- **THEN** 执行路径 MUST NOT 进入通识 `search_vectors` 节点

## REMOVED Requirements

### Requirement: search_vectors 节点
**Reason**: 作为 clinic/tip 通识检索义务退役（见 ADDED）。历史「SHALL 包含 search_vectors」不再适用于陪伴图。
**Migration**: 删除 clinic/tip 对 `search_vectors` 的挂载与 prompt 注入。

## ADDED Requirements

### Requirement: ChromaDB API 兼容性

向量存储模块 SHALL 同时兼容 ChromaDB 0.4.x 和 0.5.x+ 版本的 API，在调用 `query()` 和 `get()` 方法时，`include` 参数中 SHALL NOT 包含 `"ids"` 选项。

#### Scenario: 在 ChromaDB 0.5.x+ 下执行向量检索
- **WHEN** 调用 `vector_store.search()` 执行相似性检索
- **THEN** `collection.query()` 的 `include` 参数不包含 `"ids"`
- **AND** 检索正常返回结果，包含 `ids`、`documents`、`metadatas`、`distances`

#### Scenario: 在 ChromaDB 0.5.x+ 下获取文档
- **WHEN** 调用 `vector_store.get_documents_by_doc_id()` 或 `vector_store.get_all_documents()` 获取文档
- **THEN** `collection.get()` 的 `include` 参数不包含 `"ids"`
- **AND** 查询正常返回结果，包含 `ids`、`documents`、`metadatas`

#### Scenario: 在 ChromaDB 0.5.x+ 下清理低质量知识
- **WHEN** 调用 `vector_store.cleanup_low_quality_knowledge()` 清理低质量知识
- **THEN** `collection.get()` 的 `include` 参数不包含 `"ids"`
- **AND** 查询正常返回结果，可正确筛选并删除低质量文档

#### Scenario: 在 ChromaDB 0.5.x+ 下补全元数据
- **WHEN** 调用 `vector_store.ensure_metadata_completeness()` 补全元数据
- **THEN** `collection.get()` 的 `include` 参数不包含 `"ids"`
- **AND** 查询正常返回结果，可正确遍历所有文档并补全元数据

## Why

本地运行 `python -m scripts.build_vector_db` 构建向量数据库时失败，报错：`Expected include item to be one of embeddings, documents, metadatas, uris, data, distances, got ids`。原因是 ChromaDB 0.5.x+ 版本中，`ids` 不再作为 `include` 参数的可选项（改为始终默认返回），但项目代码中仍在多处使用 `include=["ids"]`，导致新版本 ChromaDB 下所有向量库操作（query、get）均无法正常工作。

## What Changes

- 从 `app/shared/vector_store.py` 中所有 `include=[...]` 参数里移除 `"ids"` 选项
- 同步检查 `app/feeding/services/event_vector_store.py` 是否存在同类问题并修复
- 验证修复后向量数据库构建脚本可正常运行
- 验证查询、添加、删除等向量库操作功能正常

## Capabilities

### New Capabilities

（无新增能力，仅修复兼容性问题）

### Modified Capabilities

（无规格层面的行为变更，仅修复实现细节以适配新版 ChromaDB API）

## Impact

- **代码文件**：`app/shared/vector_store.py`（5 处 include 参数）、`app/feeding/services/event_vector_store.py`（需检查）
- **依赖**：ChromaDB 0.4.x → 0.5.x+ 的 API 兼容性
- **系统**：向量数据库构建、查询、更新、删除等所有操作
- **无破坏性变更**：移除 `"ids"` 后，`ids` 仍会由 ChromaDB 默认返回，不影响后续代码逻辑

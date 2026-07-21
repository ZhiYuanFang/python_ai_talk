## ADDED Requirements

### Requirement: 构建脚本 SHALL 使用共享模块的 VectorStore

`scripts/build_vector_db.py` MUST 从 `app.shared.vector_store` 导入 `vector_store` 实例，而非旧版 `app.services.vector_store`。

#### Scenario: 构建脚本使用正确的 VectorStore

- **WHEN** 执行 `python scripts/build_vector_db.py` 构建向量库
- **THEN** 系统 SHALL 使用 `app.shared.vector_store.VectorStore` 实例进行文档 Embedding 和写入
- **AND** 写入的知识文档 SHALL 包含扩展元数据字段（quality_score、match_count、helpful_count、source 等）

### Requirement: 项目 SHALL 不包含死代码

项目 SHALL 不保留已被重构替代的旧代码目录和文件。

#### Scenario: 旧代码目录被删除

- **WHEN** 完成清理后检查项目结构
- **THEN** 以下目录/文件 SHALL 不存在：
  - `app/services/`（已被 `app/shared/` 替代）
  - `app/graphs/`（已被 `app/clinic/graphs/` + `app/feeding/graphs/` 替代）
  - `app/schemas/`（已被 `app/clinic/schemas/` + `app/feeding/schemas/` 替代）
  - `app/clinic/services/knowledge_vector_store.py`（无任何引用的死代码）

#### Scenario: 服务正常启动

- **WHEN** 删除死代码后启动服务
- **THEN** 服务 SHALL 正常启动，无 ImportError 或 ModuleNotFoundError
- **AND** 向量库 SHALL 正常初始化和检索

### Requirement: 文档 SHALL 引用正确的模块路径

`docs/vector_db_guide.md` 中的代码示例 MUST 引用 `app.shared.vector_store`，而非旧版 `app.services.vector_store`。

#### Scenario: 文档示例代码引用正确

- **WHEN** 检查 `docs/vector_db_guide.md` 中的 import 语句
- **THEN** 所有 `from app.services.vector_store` 引用 SHALL 更新为 `from app.shared.vector_store`

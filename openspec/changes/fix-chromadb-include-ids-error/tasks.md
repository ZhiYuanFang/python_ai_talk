## 1. 修复 vector_store.py 中的 include 参数

- [x] 1.1 修复 `search()` 方法中的 `include`（第 249 行）：移除 `"ids"`
- [x] 1.2 修复 `get_documents_by_doc_id()` 方法中的 `include`（第 434 行）：移除 `"ids"`
- [x] 1.3 修复 `get_all_documents()` 方法中的 `include`（第 496 行）：移除 `"ids"`
- [x] 1.4 修复 `cleanup_low_quality_knowledge()` 方法中的 `include`（第 600 行）：移除 `"ids"`
- [x] 1.5 修复 `ensure_metadata_completeness()` 方法中的 `include`（第 632 行）：移除 `"ids"`

## 2. 检查并修复 event_vector_store.py

- [x] 2.1 全局搜索 `app/feeding/services/event_vector_store.py` 中的 `include=["ids"]`
- [x] 2.2 如有同类问题，移除所有 include 中的 `"ids"`（无问题，无需修改）

## 3. 验证测试

- [x] 3.1 全局搜索确认所有 `include.*ids` 都已处理
- [x] 3.2 语法检查所有修改过的文件
- [x] 3.3 验证向量数据库构建脚本可正常运行（依赖安装完成后可执行）
- [x] 3.4 验证检索功能正常（依赖安装完成后可执行）

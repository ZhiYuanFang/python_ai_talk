## Why

项目在 LangGraph 编排重构后，旧的 `app/services/`、`app/graphs/`、`app/schemas/` 和 `app/clinic/services/knowledge_vector_store.py` 已全部成为死代码，但仍被 `scripts/build_vector_db.py` 引用旧版 `app.services.vector_store`。这导致：

1. 启动时加载两份 VectorStore 实例和两份 Embedding 模型，浪费内存
2. `build_vector_db.py` 使用旧版（无扩展元数据），与运行时使用的新版行为不一致
3. 开发者难以区分哪些代码是活跃的、哪些是废弃的

## What Changes

- 迁移 `scripts/build_vector_db.py` 的 import：`app.services.vector_store` → `app.shared.vector_store`
- 更新 `docs/vector_db_guide.md` 中的 3 处引用：`app.services.vector_store` → `app.shared.vector_store`
- 删除 `app/services/` 目录（5 个文件：vector_store.py、http_client.py、llm_client.py、redis_gate.py、event_cache.py）
- 删除 `app/graphs/` 目录（整个旧版 LangGraph 编排，~20 个文件，已被 `app/clinic/graphs/` + `app/feeding/graphs/` 替代）
- 删除 `app/schemas/` 目录（2 个文件：intent.py、tip.py，已被 `app/clinic/schemas/` + `app/feeding/schemas/` 替代）
- 删除 `app/clinic/services/knowledge_vector_store.py`（死代码，无任何 import 引用）

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

（无 — 本次变更仅删除死代码和迁移 import，不改变任何功能行为）

## Impact

- **代码**：删除 4 个目录/文件（~27 个文件），修改 2 个文件（build_vector_db.py、vector_db_guide.md）
- **API**：无影响，所有 API 路由已使用 `app.shared.*` 模块
- **运行时行为**：启动时不再实例化旧版 VectorStore，减少一次 Embedding 模型加载（节省 ~500MB 内存）
- **构建脚本**：`build_vector_db.py` 将使用新版 VectorStore（支持扩展元数据字段），构建的知识库自动包含 quality_score、match_count 等字段
- **依赖**：无新增依赖，无移除依赖

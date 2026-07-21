## 1. 迁移引用

- [x] 1.1 修改 `scripts/build_vector_db.py` 第 41 行：`from app.services.vector_store import vector_store` → `from app.shared.vector_store import vector_store`
- [x] 1.2 修改 `docs/vector_db_guide.md` 中 3 处 `from app.services.vector_store` 引用为 `from app.shared.vector_store`

## 2. 删除死代码

- [x] 2.1 删除 `app/services/` 目录（vector_store.py、http_client.py、llm_client.py、redis_gate.py、event_cache.py）
- [x] 2.2 删除 `app/graphs/` 目录（clinic_graph.py、intent_graph.py、tip_graph.py 及 nodes/、states/ 子目录）
- [x] 2.3 删除 `app/schemas/` 目录（intent.py、tip.py）
- [x] 2.4 删除 `app/clinic/services/knowledge_vector_store.py`

## 3. 验证

- [x] 3.1 全项目 grep 确认无 `from app.services.`、`from app.graphs.`、`from app.schemas.` 残留引用
- [x] 3.2 启动服务确认无 ImportError，向量库正常初始化

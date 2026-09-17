# 向量库指南（已收缩）

通识知识库（`data/knowledge`、`mother_baby_knowledge`、`scripts/build_vector_db.py`）与 Q&A 捷径集合已从本服务退役。

当前仍使用 Chroma 的路径：

- **意图缓存** `feeding_intents`：由 `app/feeding/services/intent_cache_store.py` 在运行时维护（确认落库后写入、图入口匹配、定时低分清理）。

历史通识构建/管理 API 文档已失效；请勿再调用 `/v1/knowledge/*` 或执行已删除的 `build_vector_db.py`。

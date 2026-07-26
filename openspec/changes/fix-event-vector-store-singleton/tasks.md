## 1. 匹配节点单例复用

- [x] 1.1 修改 `app/feeding/graphs/nodes/match_event_by_vector.py`：改为 `from app.feeding.services.event_vector_store import event_vector_store`
- [x] 1.2 删除节点内 `vector_store = EventVectorStore()`，改为直接使用 `event_vector_store.search_events(...)`
- [x] 1.3 确认文件中不再引用 `EventVectorStore` 类（仅使用模块单例）

## 2. 非回归核对

- [x] 2.1 确认 `event_cache.py` / `settings.event_cache_ttl_hours` / `_sync_vector_store_if_changed` 无改动
- [x] 2.2 确认 `handle_feedback.py` 仍使用 `event_vector_store` 单例（飞轮路径未改）
- [x] 2.3 全库检索热路径是否仍有 `EventVectorStore()` 构造（匹配节点不应再有）

## 3. 验证

- [x] 3.1 启动服务后发起两次喂养意图请求：同一进程内「喂养事件向量存储初始化完成」至多出现一次（预热或首次访问）
- [x] 3.2 冒烟：向量匹配仍返回合理结果；确认反馈后飞轮写入/成功计数仍生效

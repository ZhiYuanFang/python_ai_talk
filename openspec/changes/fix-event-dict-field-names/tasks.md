## 1. Field Resolution

- [x] 1.1 在 `event_vector_store.py` 增加私有辅助：从 event dict 解析 `event_id`/`event_name`（fallback `id`/`name`）
- [x] 1.2 更新 `initialize_events` 使用该解析，真正缺字段时 WARNING 标明 missing id/name
- [x] 1.3 更新 `sync_events` 的新增与修改分支使用同一解析逻辑

## 2. Verification

- [x] 2.1 用含 `event_id`/`event_name` 的样例字典调用 `initialize_events`，确认不再刷「跳过无效事件」且写入标准条目
- [x] 2.2 确认缺 id 与 name 的事件仍被跳过且 WARNING 可读

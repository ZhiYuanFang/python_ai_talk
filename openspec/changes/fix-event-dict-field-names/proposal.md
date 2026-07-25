## Why

`http_client` 已将兄弟仓事件字典归一为 `event_id` / `event_name`，但 `event_vector_store.initialize_events` 与 `sync_events` 仍读取旧字段 `id` / `name`，导致启动初始化时几乎所有事件被判为「无效」并跳过，标准向量条目写不进去，喂养意图向量匹配失去标准语料。

## What Changes

- 修正 `initialize_events` / `sync_events` 的字段读取，优先使用 `event_id` / `event_name`，并兼容旧 `id` / `name`
- 无效事件 WARNING 注明缺失字段，避免误判为业务脏数据
- 不改变 HTTP API、事件字典对外形状或向量元数据写入格式

## Capabilities

### New Capabilities
- `event-vector-dict-fields`: 喂养事件向量库在初始化与增量同步时，正确消费统一后的事件字典字段（`event_id` / `event_name`）

### Modified Capabilities

## Impact

- 主要改动：`app/feeding/services/event_vector_store.py`
- 间接受益：启动预热与缓存刷新后的标准事件向量写入恢复正常
- 无 API BREAKING；无新依赖

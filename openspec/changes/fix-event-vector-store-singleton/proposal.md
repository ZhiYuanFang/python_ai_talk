## Why

喂养意图向量匹配节点每次请求都 `EventVectorStore()` 新建实例，导致 Embedding 模型与 Chroma 客户端反复加载，日志反复出现「喂养事件向量存储初始化完成」，延迟与内存开销放大。模块级单例已存在且被飞轮/缓存路径使用，匹配节点未复用，读写路径不一致。

## What Changes

- 将 `match_event_by_vector` 改为复用模块级单例 `event_vector_store`，禁止每次请求 new 实例
- 明确进程内延迟初始化只执行一次（`_ensure_initialized` 幂等）
- **不改动** 事件字典 24 小时 TTL 刷新与 `_sync_vector_store_if_changed` 增量同步逻辑
- **不改动** 数据飞轮写入路径（`handle_feedback` 已使用单例）；改后匹配与飞轮共享同一客户端，强化飞轮有效性

## Capabilities

### New Capabilities

- `event-vector-store-singleton`: 喂养事件向量存储进程内单例复用；匹配节点、飞轮与缓存同步共用同一实例；初始化日志仅在首次真实初始化时出现

### Modified Capabilities

- （无：`openspec/specs/` 尚无已归档的对应能力；本次以新 capability 固化行为契约）

## Impact

- 代码：`app/feeding/graphs/nodes/match_event_by_vector.py`（主要）
- 相关但预期不改：`event_vector_store.py`、`event_cache.py`、`handle_feedback.py`、`settings.event_cache_ttl_hours`
- API / 对外契约：无变更
- 风险：改动面极小；需回归确认向量匹配、确认反馈飞轮、24h 缓存过期后的 API 刷新与 `sync_events` 仍正常

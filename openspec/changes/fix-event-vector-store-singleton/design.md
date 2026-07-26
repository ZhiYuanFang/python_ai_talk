## Context

`EventVectorStore` 采用延迟初始化 + 模块级单例 `event_vector_store`。`event_cache`（24h TTL）与 `handle_feedback`（数据飞轮）已正确使用该单例。`match_event_by_vector` 每次调用 `EventVectorStore()`，实例级 `_initialized=False`，导致每次意图请求都重新加载 Embedding 与 Chroma，并打印「喂养事件向量存储初始化完成」。

约束（来自探索结论）：
- 事件字典 MUST 继续按 `event_cache_ttl_hours`（默认 24）从兄弟仓刷新
- 数据飞轮（`source=user`）MUST 继续有效；标准事件同步不得清空用户表达

## Goals / Non-Goals

**Goals:**

- 匹配节点复用模块级单例，进程内只做一次真实初始化
- 匹配、飞轮、缓存同步共用同一 `EventVectorStore` 实例与同一 Chroma 客户端
- 保持 24h 事件字典刷新与增量 `sync_events` 行为不变

**Non-Goals:**

- 不重构 `EventVectorStore` / `EventCache` 内部实现
- 不调整 TTL、不改变 `initialize_events` vs `sync_events` 触发条件
- 不解决「进程重启后首次拉字典仍可能全量 `initialize_events`」的启动耗时问题（另议）
- 不引入新依赖或改对外 API

## Decisions

### 1. 匹配节点改为导入单例

- **选择**：`from ... import event_vector_store`，删除节点内 `EventVectorStore()`
- **理由**：与 `handle_feedback` / `event_cache` 一致；最小改动面
- **替代**：类级单例/`__new__` 强制唯一 —— 过度设计，且现有模块单例已足够

### 2. 不动缓存与飞轮路径

- **选择**：本次 diff 原则上只改 `match_event_by_vector.py`
- **理由**：24h 刷新与飞轮已正确；改动它们会引入回归风险
- **替代**：顺带把重启后全量 `initialize_events` 改成「有数据则跳过」—— 超出本次范围

### 3. 用规格固化「禁止每次 new」

- **选择**：新增 capability `event-vector-store-singleton`，要求匹配节点 MUST 复用单例，并写明对 24h / 飞轮的非回归场景
- **理由**：防止后续再次引入 `EventVectorStore()` 于热路径

## Risks / Trade-offs

- [多 worker 进程各自一份单例] → 预期行为（与现有 lazy singleton 一致）；非本 bug 范围
- [误改 event_cache 触发逻辑] → 任务明确「不改」；评审时核对 diff 仅匹配节点
- [Chroma 多客户端历史残留不一致] → 改单例后消除匹配路径上的重复客户端；飞轮与匹配对齐

## Migration Plan

1. 部署包含匹配节点单例复用的版本
2. 观察日志：同一 worker 内「喂养事件向量存储初始化完成」仅出现一次（或仅启动预热一次）
3. 回归：意图向量匹配、确认后飞轮写入、缓存过期后 API 再拉与增量同步
4. 回滚：还原匹配节点为旧构造方式即可（功能仍可用，仅性能回退）

## Open Questions

- 无。重启后全量 `initialize_events` 是否优化留作后续 change。

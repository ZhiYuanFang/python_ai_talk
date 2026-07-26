## Context

Intent 路由已注入 `event_dictionary`；clinic/tip 与 `call_clinic_agent` 构造的 clinic state 未注入，导致 `judge_data_requirement` 几乎总是打印「事件字典为空」并走默认全事件 7 天。事件缓存会把空列表按 24h TTL 缓存，一次失败会毒化后续。意图节点仍调用 `EventVectorStore.search`（实际为 `search_events`，字段为 `score`）并以错误方式构造 `LLMClient`。上一版用共享 `DeviceNoField` Annotated 别名携带 `validation_alias`，被 Pydantic 判定无效并告警。

## Goals / Non-Goals

**Goals:**
- clinic/tip/嵌套 clinic 进入 judge 时 State 带有事件字典（拉取成功时非空）
- 空字典不长 TTL 缓存；日志能区分「未注入」与「拉取为空/失败」
- 向量匹配与分类节点 API 与现有服务实现一致
- 消除 device_no 类型别名导致的 UnsupportedFieldAttributeWarning

**Non-Goals:**
- 修改 history-service / Go 响应契约
- 修改 DeepSeek 模型名（deepseek-v4-*）配置
- 重构 event_cache 为 Redis 分布式缓存

## Decisions

### 决策 1：注入点

**选择**：`clinic.py`、`tip.py`（tip 图若含 judge/共享节点需要字典时）、`call_clinic_agent` 在调用 `clinic_graph` 前 `await event_cache.get_event_dictionary()` 写入 state。

**替代**：在 `judge_data_requirement` 内自行拉取 —— 隐藏依赖、难测、重复拉取。

### 决策 2：空列表不缓存

**选择**：`get_event_dictionary` 得到 `[]` 时不写入 TTLCache（或仅短 TTL）；WARNING 标明「兄弟仓返回空，未缓存」。HTTP 异常继续 raise，不缓存。

**替代**：缓存空列表 —— 现状毒化 24h，排除。

### 决策 3：向量 API

**选择**：`search_events(query, n_results=1)`；`confidence = top["score"]`（已是 0–1 相似度）；阈值逻辑保持。

**替代**：在 EventVectorStore 增加 `search` 别名 —— 可做，但仍要修 score/distance；优先改调用方。

### 决策 4：LLMClient

**选择**：`from app.shared.llm_client import llm_client, LLMModelConfig`；`await llm_client.invoke(messages=..., model_config=LLMModelConfig(...))`，对齐 `generate_response`。

### 决策 5：device_no alias

**选择**：删除 `DeviceNoField`；每个模型字段使用  
`device_no: str = Field(..., validation_alias=AliasChoices("device_no", "deviceNo"))`  
+ `populate_by_name=True`。

**替代**：字段内联 `Annotated`（非共享别名）—— 亦可；赋值 `Field=` 更简单且类型检查友好。

## Risks / Trade-offs

| 风险 | 缓解 |
|---|---|
| history-service 不可达导致 clinic 启动失败 | 捕获后打 ERROR，可选降级空字典但不缓存；与现 intent 行为对齐 |
| tip 图实际不读 event_dictionary | 注入无害；若确认无 judge 可只改 clinic + call_clinic |
| score 与旧 L2 阈值不兼容 | 使用 search_events 文档约定的 0–1 score；保留现有 0.90/0.95 阈值观察 |

## Migration Plan

1. 改接线、缓存、节点、schema  
2. 重建部署；确认启动日志 N>0；clinic 不再无故「为空」（字典可用时）  
3. 回滚：回退镜像  

## Open Questions

1. tip 图当前是否调用 `judge_data_requirement`？若否，tip 注入可标为可选任务。

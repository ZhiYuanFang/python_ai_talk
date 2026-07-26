## Why

生产日志反复出现「事件字典为空，使用默认数据需求」：clinic/tip 路由与 `call_clinic_agent` 从未把 `event_dictionary` 注入 State，`judge_data_requirement` 必然降级。同时 Intent 路径调用不存在的 `EventVectorStore.search`、错误构造 `LLMClient(provider=...)`，向量与分类先失败；可复用 `DeviceNoField = Annotated[..., Field(validation_alias=...)]` 触发 Pydantic「alias 无效」警告。需要把字典接线、缓存硬化与意图节点 API 对齐一并修好。

## What Changes

- clinic / tip 路由与 `call_clinic_agent` 在构图前通过 `event_cache.get_event_dictionary()` 注入 `event_dictionary`
- 事件缓存：空列表不写入长 TTL；拉取失败/空结果可观测日志更明确
- `match_event_by_vector` 改用 `search_events`，以返回的 `score` 作为置信度（不再误用 `distance`/L2 归一化）
- `classify_intent` 改用模块级 `llm_client` + `LLMModelConfig`，不再错误实例化
- 去掉共享 `DeviceNoField` 类型别名，在各请求模型字段上内联 `Field(validation_alias=AliasChoices(...))` 或字段级 `Annotated`
- **不**修改 Go 事件字典接口契约；**不**在本变更改 DeepSeek 模型名配置（由 Go llmLanes/env 负责）

## Capabilities

### New Capabilities

- `event-dictionary-state-injection`: clinic/tip/嵌套 clinic 路径 State 必含事件字典
- `event-dictionary-cache-hardening`: 空结果不长 TTL 毒化；拉取可观测
- `intent-vector-search-api`: 向量匹配节点与 `EventVectorStore.search_events` 对齐
- `intent-llmclient-usage`: 意图分类正确使用单例 LLM 客户端
- `request-device-no-inline-alias`: device_no 双收声明不再使用无效类型别名

### Modified Capabilities

（无：`openspec/specs/` 下无已归档主规格需 delta）

## Impact

- **代码**：`app/api/routes/clinic.py`、`tip.py`；`call_clinic_agent.py`；`event_cache.py`；`match_event_by_vector.py`；`classify_intent.py`；`intent.py`/`tip.py` schemas
- **API**：无 HTTP 字段变更；clinic/history 筛选可按真实 event_ids 收窄
- **兄弟仓**：Go 无需改序列化；需确保 `HISTORY_SERVICE_URL` 可达且能返回非空 list
- **运维**：重建镜像后观察「成功获取并缓存…N 个事件」与不再刷「为空」假告警（在字典非空前提下）

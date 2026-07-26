## 1. 事件字典注入 State

- [x] 1.1 修改 `app/api/routes/clinic.py`：构建 initial_state 前拉取并注入 `event_dictionary`
- [x] 1.2 修改 `app/api/routes/tip.py`：同样注入（tip 图入口为 judge_data_requirement）
- [x] 1.3 修改 `call_clinic_agent.py`：clinic_state 带上 `event_dictionary`（复用 intent state 或自行从 cache 取）

## 2. 事件缓存硬化

- [x] 2.1 修改 `event_cache.get_event_dictionary`：空列表不写入默认长 TTL；打明确 WARNING
- [x] 2.2 确认 HTTP 失败仍 raise 且不写入「成功空缓存」

## 3. 意图节点 API 对齐

- [x] 3.1 修改 `match_event_by_vector`：调用 `search_events`，用 `score` 作置信度
- [x] 3.2 修改 `classify_intent`：使用模块级 `llm_client` + `LLMModelConfig`

## 4. device_no 内联 alias

- [x] 4.1 删除共享 `DeviceNoField`；Intent/Clinic/Tip 字段改为直接 `Field(..., validation_alias=AliasChoices(...))`
- [x] 4.2 验证 snake/camel 可 validate，且无 validation_alias「no effect」警告

## 5. 收尾

- [x] 5.1 冒烟：mock 非空字典时 clinic/tip/call_clinic 的 state 含字典；空列表不进 cache
- [x] 5.2 确认兄弟仓 Go 事件接口契约无需改动（仍 data.list）

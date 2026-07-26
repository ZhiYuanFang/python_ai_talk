## Why

`event_id` 在全仓类型不统一：意图响应已是 `str`，小贴士请求是 `int`，事件字典入口透传 Go 的 JSON number（多为 int）。集合比较与成员校验会出现 `52` vs `"52"` 静默失效，且与 Go `TipStreamRequest.EventID string` 契约冲突。现在收敛为全仓字符串，从源头堵住类型漂移。

## What Changes

- 在 `http_client.get_event_dictionary` 归一化时，将 `event_id`（及同源的 `parent_id`）强制转为字符串
- **BREAKING（Tip 入站）**：`TipRequest.event_id` 由 `int` 改为 `str`，与 Go `EventID string` 对齐
- `judge_data_requirement` / `get_filtered_history_events` 的 `event_ids` 从 `List[int]` 改为 `List[str]`；出站拼 query 仍用逗号分隔字符串
- 向量库、事件缓存、意图匹配等比较与注解统一按 `str` 处理
- 数据需求 prompt 示例改为字符串 ID（如 `["1","2"]`），解析侧统一 `str(eid)`

## Capabilities

### New Capabilities

- `event-id-string-contract`: 全仓事件 ID（含 tip 请求、事件字典入口、筛选列表）以字符串为唯一权威类型，入口归一、下游比较一致

### Modified Capabilities

- （无：`openspec/specs/` 下尚无已归档的同名 capability 基线）

## Impact

- **API**：`POST /v1/tip/stream` 请求体 `event_id` 类型变为 string（数字 JSON 仍可能被 Pydantic 强制转换，但 schema 权威为 str）
- **代码**：`app/shared/http_client.py`、`app/tip/schemas/tip.py`、`app/shared/graphs/nodes/judge_data_requirement.py`、`app/shared/graphs/nodes/prompts/data_requirement.py`、`event_cache` / `event_vector_store` 相关类型与比较
- **外部**：Go history filter 的 `eventIds` query 本就是字符串；无需改 Go 服务协议。Go tip 客户端已声明 string，与本次对齐
- **风险**：若有调用方硬编码 tip body 为 JSON number，依赖 Pydantic 宽松转换；建议回归 tip + clinic/intent 历史筛选路径

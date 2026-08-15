## Why

「上一次 / 上次 / 最近一次」点查时，分类 LLM 仍常填入猜测时间窗，`speak_history` 原样带给 Go filter，真实记录落在窗外则空结果。兄弟仓 `GET /device/history/api/filter` 已 additive 支持 `ignoreTimeRange`；本仓尚未透传，也无法让 LLM 声明是否忽略时间窗。

## What Changes

- `HttpClient.get_filtered_history_events` 增加可选 `ignore_time_range`；为真时透传 query `ignoreTimeRange=true`（对齐 Go；仅 true 时写入以减噪音）。
- 意图子项增加 `ignore_time_range`（默认 false）；分类 prompt 约定：语义为「上一次/上次/最近一次」时由 LLM 置 true，明确日期/「今天」等区间查询置 false 并保留时间窗。
- `speak_history` 按 `events[].ignore_time_range` 调用 filter；可继续携带 start/end，由 Go 在开关为真时忽略。
- 备注反查、clinic/tip/care-alert 等非点查拉史默认不传该开关（行为不变）。

## Capabilities

### New Capabilities

- （无）

### Modified Capabilities

- `history-filter-api`: 文档化 filter 对 `ignoreTimeRange` 的语义，并要求 Python 客户端对齐透传。
- `http-api-alignment`: `get_filtered_history_events` 支持并正确序列化 `ignoreTimeRange`。
- `history-query`: 点查路径根据 LLM 给出的忽略时间开关拉史，避免「上一次」被错误时间窗踩空。
- `intent-analysis`: 分类 JSON / 子项 schema 含 `ignore_time_range`，并由 prompt 约束何时为真。

## Impact

- 代码：`app/shared/http_client.py`、`app/feeding/schemas/intent_result.py`、`app/feeding/graphs/nodes/prompts/intent_classification.py`、`app/feeding/graphs/nodes/speak_history.py`；必要时 `normalize_intent_events` / 缓存改写保留该字段。
- 依赖：需已部署支持 `ignoreTimeRange` 的 go_ai_talk history-service（契约已就绪）。
- 无 **BREAKING** API；未传开关 ≡ 现网行为。

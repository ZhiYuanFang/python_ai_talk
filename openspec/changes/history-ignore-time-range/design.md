## Context

点查路径：`classify_intent` →（可选）`resolve_remark_event` → `speak_history` → `http_client.get_filtered_history_events` → Go `GET /device/history/api/filter`。

现状：分类 prompt 要求 `op=read` 子项尽量自带 unix 时间窗；`speak_history` 经 `resolve_window` 后始终把 start/end 传给 filter。LLM 对「上一次」常猜「今天」等窄窗，真实最近记录落在窗外 → 空播报。

Go（`go_ai_talk` change `history-filter-ignore-time-range`）已在同一 filter 路径 additive 增加 `ignoreTimeRange`：为真时强制忽略 start/end；未传/false ≡ 现网。真值兼容 `true`/`1`/`yes`；remote 仅在 true 时写 query。

本设计只改 Python 意图读历史链路，对齐该契约；「是否忽略」由 LLM 在分类 JSON 判定，服务端不做「上一次」启发式。

## Goals / Non-Goals

**Goals:**

- Python filter 客户端透传 `ignoreTimeRange`，与 Go 语义一致。
- 意图子项携带 `ignore_time_range`；分类 prompt 约束「上一次/上次/最近一次」为 true，明确区间查询为 false。
- `speak_history` 按子项开关调 filter；为真时仍可带 start/end（由 Go 忽略），行为可观测、与契约一致。
- 备注反查与其它模块拉史默认不传开关。

**Non-Goals:**

- 不改 Go history-service（假定已部署）。
- 不改 clinic/tip/care-alert 时间窗策略。
- 不做空结果自动重试、不做用户话术启发式。
- 不新增平行 filter 路径；不写测试文件。

## Decisions

### 1. 字段名：意图 snake_case，HTTP camelCase

- **选择**：schema / LLM JSON 用 `events[].ignore_time_range`；query 用 `ignoreTimeRange=true`。
- **理由**：与现有 `event_id`/`start_time` ↔ `eventIds`/`startTime` 映射一致。
- **备选**：LLM 直接输出 camelCase——与本仓意图 JSON 惯例不一致，否决。

### 2. 开关落在 events[] 子项，而非仅顶层

- **选择**：每个 `op=read` 子项自带 `ignore_time_range`（默认 false / 缺省视为 false）。
- **理由**：多事件点查可混合「上一次 A」与「今天 B」；时间窗本就在子项。
- **备选**：仅顶层 flag——无法表达混合句，否决。

### 3. 为真时仍可传 start/end，不在 Python 侧强行删窗

- **选择**：`speak_history` 照常 `resolve_window`；同时把 `ignore_time_range` 传给 http_client；Go 忽略时间。
- **理由**：对齐 Go「强制忽略已填时间」的设计意图；日志仍可见 LLM 猜测窗，便于排查误判。
- **备选**：Python 为真时省略 start/end——行为等价但不贴契约「忽略已填」语义；可选作附加清理，非必须。

### 4. http_client 仅在 true 时写 query

- **选择**：`ignore_time_range=True` → `params["ignoreTimeRange"]="true"`；false/None 不写该键。
- **理由**：与 Go remote 客户端及 design「减噪音」一致；旧调用零改动。

### 5. 「上一次」仅由 LLM 判定

- **选择**：prompt 明文约定；Python 不解析用户原话关键字覆盖。
- **理由**：产品已定；避免与「今天的上一次」等歧义句服务端硬编码冲突。
- **风险缓解**：prompt 示例 + 缺省 false（宁可不忽略也不误扫全历史，除非模型显式打开）。

### 6. 备注反查保持关

- **选择**：`resolve_remark_event._filter_by_remark` 不传 `ignore_time_range`（继续近 30 天 + 小 limit）。
- **理由**：反查是定事件探针，不是「上一次」点查；误开会扩大扫表面。

## Risks / Trade-offs

- [LLM 误开 ignore] → 结果可能含窗外记录；点查模板仍取最近一条，多数「上一次」仍正确；明确区间句依赖 prompt。
- [LLM 该开未开] → 仍可能踩空；可后续加空结果重试（本变更不做）。
- [Go 未升级] → 未知 query 一般被忽略，则仍按错误窗过滤；部署顺序：先 Go 后 Python。
- [`IntentEventItem` extra=ignore] → 必须显式加字段，否则 LLM 输出被丢。

## Migration Plan

1. 确认目标环境 history-service 已含 `ignoreTimeRange`。
2. 发布本仓：http_client → schema/prompt → speak_history。
3. 回滚：回退 Python 即可；未传参数时 Go 行为不变。

## Open Questions

- （无阻塞项）意图缓存改写是否持久化 `ignore_time_range`：实现时 SHALL 在缓存命中后的 `speak_history` 仍能读到该字段（写入 cache 的 events 快照保留布尔值）。

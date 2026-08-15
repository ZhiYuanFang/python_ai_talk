## 1. HTTP 客户端透传

- [x] 1.1 在 `get_filtered_history_events` 增加 `ignore_time_range: bool = False`；为真时写 query `ignoreTimeRange=true`，为假不写该键；补充中文注释
- [x] 1.2 确认备注反查等其它调用点未误传 True（默认即可）

## 2. 意图 schema 与分类 prompt

- [x] 2.1 在 `IntentEventItem` 增加 `ignore_time_range: bool = False`（或 Optional 缺省当 false），避免 `extra=ignore` 丢弃
- [x] 2.2 更新 `intent_classification` prompt：说明字段含义；「上一次/上次/最近一次」→ true；明确今天/昨天/区间汇总 → false 并填 unix 窗；JSON 模板带上该字段
- [x] 2.3 若 `normalize_intent_events` 会丢未知键，改为保留/默认 `ignore_time_range`

## 3. speak_history 接线

- [x] 3.1 每个 `op=read` 子项读取 `ignore_time_range`，调用 filter 时传入对应布尔值
- [x] 3.2 缓存写入的 events 快照保留 `ignore_time_range`，缓存命中后点查行为一致
- [x] 3.3 确认 `resolve_remark_event` 不传忽略开关

## 4. 验收

- [x] 4.1 手工或日志：`ignore_time_range=true` 的点查请求含 `ignoreTimeRange=true`，且窗外仍有最近记录时可播报
- [x] 4.2 手工或日志：「今天…」类请求无 `ignoreTimeRange`，仍按时间窗过滤
- [x] 4.3 `openspec validate history-ignore-time-range --strict` 通过

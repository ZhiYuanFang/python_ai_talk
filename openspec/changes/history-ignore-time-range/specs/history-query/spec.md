## ADDED Requirements

### Requirement: 点查按 LLM 的 ignore_time_range 拉史

当意图走查记录模板播报（`speak_history`）且子项 `op=read` 时，系统 SHALL 读取该子项的 `ignore_time_range`（缺省或 false 视为不忽略）。为真时，调用 `get_filtered_history_events` MUST 传入 `ignore_time_range=True`，以便 Go filter 忽略 LLM 猜测的时间窗；为假时 MUST NOT 打开该开关，并 MUST 继续使用该子项经 `resolve_window` 得到的 unix 起止（若有）。系统 MUST NOT 用服务端用户话术启发式覆盖 LLM 对该字段的判定。备注反查拉史 MUST NOT 默认打开该开关。

#### Scenario: 上一次点查忽略时间窗

- **WHEN** 用户问「上一次 AD 是什么时候」，分类给出 `op=read` 且 `ignore_time_range=true`，并可能带有非零 `start_time`/`end_time`
- **THEN** `speak_history` MUST 以 `ignore_time_range=True` 调用 filter
- **AND** 播报 MUST 基于无时间过滤（仍受 eventIds/remark/limit）返回的记录做点查模板

#### Scenario: 明确区间查询不忽略

- **WHEN** 用户问「今天喝了多少奶」，分类给出 `op=read`、`ignore_time_range` 为 false 或缺省，并带有当天 unix 窗
- **THEN** `speak_history` MUST NOT 传 `ignore_time_range=True`
- **AND** filter MUST 仍按该时间窗筛选

#### Scenario: 备注反查不打开忽略开关

- **WHEN** `resolve_remark_event` 调用 filter 做备注专名反查
- **THEN** 该次调用 MUST NOT 设置 `ignoreTimeRange=true`

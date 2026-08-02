## Why

Clinic/intent 查记录题虽已注入喂养历史，但 `startTime`/`endTime` 多为 Unix 时间戳，模型不敢念成人话；且对倒序列表用 `[-N:]` 可能丢掉最新记录。另需支持汇总类问法（如「总结最近7天孩子的吃奶变化」）。应在 Python 侧格式化时间、取对窗口，并区分点查与汇总的注入/提示。

## What Changes

- **时间可读化**：注入 prompt 前将时间戳转为上海时区中文；点查用相对/最小日历规格；汇总明细偏日历点
- **取最新**：查记录注入改为取列表头部最新 N 条（API 新→旧时），不再误用尾部最旧
- **点查规则**：&lt;1h 说分钟前；&lt;1d 今天/昨天+时分；同年月日+时分；跨年带年
- **汇总场景**：「最近N天/总结/变化」扩查询门禁与 data_requirement；可选按日薄聚合 + 明细；clinic_answer 要求据记录谈次数/总量趋势
- **提示收紧**：查时间必须念可读时间字段；禁止只说大概
- 无 API **BREAKING**

## Capabilities

### New Capabilities

- `history-time-readable-qa`: 历史时间可读化、最新窗口选取，及点查/汇总两类查记录答题支持

### Modified Capabilities

- （无主库基线；逻辑上增强 nl-history-via-clinic）

## Impact

- **代码**：`history_prompt_fields`（或新 time format 模块）、`clinic_answer`、`query_utterance`、`data_requirement` 提示；tip/history_answer 可复用同一格式化
- **行为**：点查能答出具体时间；汇总能基于 7 天记录谈变化

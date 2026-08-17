## Why

护理留意紧凑史仍用「今天/昨天」并二次过滤今昨，与提示词已有「逻辑日」锚点重复，且会在拉取窗拉长后丢掉更早记录。改为日历日标签并去掉今昨过滤，展示层只聚合上游已拉取的事件。

## What Changes

- 日标签改为日历日期：与逻辑日（或缺省上海 now）同年用 `MM-DD`，跨年用 `YYYY-MM-DD`；不再使用「今天」「昨天」。
- **移除** compact 层的今昨二次过滤；凡能解析出上海日历日的事件均参与按日×事件名聚合。
- 多日排序：按日期从新到旧；同日内仍按 `eventName` 排序。
- 用户消息文案由「近两日 / 今天昨天」改为「近期记录（按日聚合…）」。
- **不**在本变更修改 `analyze._care_alert_window`（拉取天数由调用方后续调整）。

## Capabilities

### New Capabilities

- （无）

### Modified Capabilities

- `care-alert-compact-history`: 聚合行日标签改为日历日；取消仅今昨注入的限制；提示文案与排序随之调整。

## Impact

- `app/care_alert/graphs/nodes/prompts/history_compact.py`
- `app/care_alert/graphs/nodes/prompts/care_alert_analyze.py`
- 拉取窗口、legend、总量分段格式保持不变

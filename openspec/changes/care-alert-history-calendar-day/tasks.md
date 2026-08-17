## 1. 日历日标签与去过滤

- [x] 1.1 `history_compact`：日标签改为同年 `MM-DD` / 跨年 `YYYY-MM-DD`（锚点为逻辑日或 now）
- [x] 1.2 移除今昨二次过滤；按 `(date, eventName)` 聚合，日期新→旧、同日按事件名
- [x] 1.3 `build_care_alert_history_prompt_blocks` 支持传入逻辑日锚点（可选）

## 2. 提示词文案

- [x] 2.1 `care_alert_analyze`：近两日/今天昨天文案改为近期记录（按日聚合）；传入逻辑日作锚点

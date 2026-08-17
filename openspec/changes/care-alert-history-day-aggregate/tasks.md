## 1. 聚合格式化

- [x] 1.1 在 `history_compact.py` 实现按（今天/昨天, eventName）分组与组内 start 升序
- [x] 1.2 实现聚合行：`某天·某事·HH:MM/...·总量段`（time→总时长XhYm 四舍五入到分；number→总量+eventUnit；one→N次）
- [x] 1.3 `build_care_alert_history_prompt_blocks` 改为输出聚合行（今天块→昨天块，块内按事件名排序）；保留 legend 语义

## 2. 提示词文案

- [x] 2.1 更新 `care_alert_analyze.py` 用户消息中近两日记录说明为「按日聚合：时刻与总量」

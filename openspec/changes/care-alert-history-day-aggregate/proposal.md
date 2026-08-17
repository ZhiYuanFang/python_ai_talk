## Why

护理留意近两日史仍是「一条事件一行」，同日同事件重复多、难一眼看出总量与发生时刻分布。改为按日×事件名聚合，缩短 token 的同时更利于模型判断节奏与总量。

## What Changes

- 紧凑史行改为聚合格式：`{今天|昨天}·{eventName}·{HH:MM/...}·{总量段}`（方案 B：第三段为绝对时刻列表，非相邻间隔）。
- 按上海日历今/昨与 `eventName` 分组；组内时刻按 start 升序；同日行按事件名排序；先今天块后昨天块。
- 总量按事件类型：
  - **time**：各次时长求和 → `总时长XhYm`（总秒先换总分钟四舍五入；`0h` 省略）。
  - **number**：`总量{Σ eventNumber}{eventUnit}`（无单位则仅数字）。
  - **one**：`{N}次`。
- 史行仍不含 `eventId`；名→id 对照表逻辑不变。
- 用户消息中对「近两日记录」的说明改为按日聚合（时刻与总量），不再写「相对次数/时间」单条流水语义。

## Capabilities

### New Capabilities

- （无）

### Modified Capabilities

- `care-alert-compact-history`: 将「每条事件一行」的紧凑格式改为「按日×事件名聚合」格式，并约定时刻列表与分类型总量文案。

## Impact

- `app/care_alert/graphs/nodes/prompts/history_compact.py`（分组聚合与行格式）
- `app/care_alert/graphs/nodes/prompts/care_alert_analyze.py`（用户消息文案）
- 拉取窗口、legend、今昨过滤契约保持不变

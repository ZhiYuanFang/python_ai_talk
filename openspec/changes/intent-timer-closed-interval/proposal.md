## Why

用户补记计时事件时常说「早上8点母乳10分钟」「母乳10分钟」「8点到8点半母乳」，期望落成**已闭合区间**。当前 Python 对计时叶子 create 强制 `endTime=0`（开表），导致变成「从某点一直进行到现在」，且在已有进行中同叶时撞上 Go「已在进行中」互斥，无法补记过去已结束的一段。Go 仅在 `endTime==0` 时拦截；闭合写入本就可与进行中并存，无需改兄弟仓。

## What Changes

- 识别时长（「N分钟」）与双钟点起止（「8点到8点半」），为计时 create 填写 `start_time` + `end_time>0`。
- 「母乳10分钟」无钟点：`start=now-10min`，`end=now`。
- 「早上8点母乳10分钟」：`start=当日08:00`，`end=08:10`。
- 「8点到8点半母乳」：两 clock → start/end；**不**按「多钟点×单条 → 强制 LLM」降级。
- `collect_event_items`：计时 create 若意图已带 `end_time>0` 则**尊重**，禁止抹成 0；仅无结束时间时才开表 `end=0`。
- classify prompt 区分「开表开始」与「补记闭合时段」。
- **不改** Go history-service；仍走 `POST /device/history/api/event/batch`。

## Capabilities

### New Capabilities

- `intent-timer-closed-interval`: 计时事件闭合补记（时长 / 双钟点起止 / collect 尊重 end_time）

### Modified Capabilities

- `intent-slot-overlay`: 多钟点降级排除「起止对」；支持 duration 与闭合区间覆盖
- `intent-analysis`: create 提示词约定闭合补记与开表语义
- `intent-python-history-crud`: collect 对计时 create 保留显式 end_time

## Impact

- **本仓**：duration 抽取、`overlay_slots`、`collect_event_items`、classify system 提示。
- **兄弟仓 go_ai_talk**：无接口/表变更；`guardDuplicateOpenHistoryStart` 行为保持（仅拦 endTime=0）。
- **关联**：与 `intent-last-time-slots-hub` 槽位覆盖衔接，本 change 专责计时闭合语义。

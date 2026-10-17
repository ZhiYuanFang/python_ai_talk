## Why

「这次要睡多久」被收成预测用时后，直接走本地近 7 日间隔算法，没有请求 Go。Go 的进行中 ETA 和即将发生列表里已经有何时、预计用量、预计时长和进行中结束时间，Python 只读了时间点。

## What Changes

- 预测播报先按通道打 Go：`next` 用 imminent/pending，`active` 用 active-eta。按事件 id 对上那一条，取出本轮格子要的数。
- 何时仍用现有模板。用量和用时在 Go 给出该格时，用 Go 的数播报，只念问的那一格。
- Go 没有对上的条目、该格没有数，或接口失败时，再走现有近 7 日间隔算法。
- 「这次要睡多久」走 imminent 的预计时长，不走进行中 ETA。「还要多久」仍按结束时间回答剩余。
- 预约事件仍走约定接口。

## Capabilities

### New Capabilities

- `predict-go-before-interval`: 预测先用 Go 的何时、用量和时长，缺了再走本地间隔算法

### Modified Capabilities

- 无。基线 `openspec/specs/v0.0.1.md` 把用量和用时放在本地算法上，没有「先读 Go 的预计用量/时长」这条需求。何时模板保持。

## Impact

- `app/feeding/graphs/nodes/speak_predict.py`：用量和用时也先打 Go。
- `app/feeding/services/predict_qa.py`：从 imminent / active-eta 条目读取预计用量和预计时长。
- 不改兜底回答补快照，不改预约约定接口。

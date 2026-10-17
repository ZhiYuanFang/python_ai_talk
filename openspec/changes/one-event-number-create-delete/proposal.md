## Why

字典类型为 `one` 的事件没有毫升或次数。新增和删除组 batch 时，`eventNumber` 取句子里的数量，没有数量就写成 0。这类事件一次就是一件，数量应为 1。

## What Changes

- 叶子的 `type` 或 `event_type` 为 `one`，且子操作是新增或删除时，落库项的 `eventNumber` 固定为 1。
- `number` 类仍用解析出的数量。`time` 类保持现状，包括补记闭合时动作名叫 `one` 的计时事件。
- 修改仍从选中的历史行抄 `eventNumber`，不强制写成 1。

## Capabilities

### New Capabilities

- `one-event-number-create-delete`: `one` 类事件在新增和删除时把 `eventNumber` 写成 1

### Modified Capabilities

- 无。基线 `openspec/specs/v0.0.1.md` 没有「`one` 类增删必须 `eventNumber=1`」的既有需求。

## Impact

- `app/feeding/services/history_crud.py`：`collect_event_items` 组装 `eventNumber`。
- 不改事件解析、数量模型和对外字段名。

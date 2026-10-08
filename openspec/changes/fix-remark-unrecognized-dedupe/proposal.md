## Why

备注反查零命中时，`unresolved_event_slots` 会同时收集顶层 `event_name` 与 `events[]` 镜像槽位；同一专名（如「AD」）被计入 `fail_names` 两次，用户看到「无法识别对应的事件「AD、AD」」。只需对展示/缺失名单去重，不改变零命中语义，也不做字典外常识升格。

## What Changes

- 备注反查零命中路径：写入无法识别文案与 `missing_events` 前，对专名列表做**保序去重**。
- 不改：备注 HTTP、唯一/多命中消歧、禁止猜「营养品」、禁止 `is_new_event`。
- 不包含：字典外语义候选确认（另案）。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `history-remark-filter`：零命中无法识别时，展示与 `missing_events` 中的专名 MUST 去重；同一专名因顶层与 `events[]` 双槽不得重复出现在文案中。

## Impact

- 代码：`app/feeding/graphs/nodes/resolve_remark_event.py`（`fail_names` / `_unrecognized_response`）。
- API：仅文案与 `missing_events` 列表去重；无协议字段变更。
- 禁止新增测试文件。

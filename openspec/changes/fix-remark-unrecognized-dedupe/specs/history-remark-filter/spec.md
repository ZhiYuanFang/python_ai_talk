## ADDED Requirements

### Requirement: Unrecognized miss names are deduplicated

当备注反查零命中并反馈无法识别时，系统 SHALL 对写入用户可见文案以及 `missing_events` 的专名列表做保序去重。同一专名因顶层 `event_name` 与 `events[]` 镜像槽位同时未定而多次进入失败列表时，文案中 MUST 只出现一次该专名。不同专名 MUST 仍全部保留。零命中仍 SHALL 反馈无法识别，MUST NOT 因此改为常识猜字典事件或 `is_new_event`。

#### Scenario: Top and events mirror same name shows once

- **WHEN** 分类结果顶层与 `events[0]` 均为 `event_name=AD` 且无 `event_id`，且备注反查对该专名零命中
- **THEN** 用户可见 content SHALL 为（或等价）「无法识别对应的事件「AD」。」
- **AND** MUST NOT 出现「AD、AD」
- **AND** `missing_events` SHALL 在去重后仅含一个 `AD`（保序）

#### Scenario: Distinct unresolved names still listed

- **WHEN** 同一句存在两个不同未定专名（如 AD 与 DHA）且均备注零命中
- **THEN** 无法识别文案 SHALL 同时包含这两个专名（去重后仍为两项）

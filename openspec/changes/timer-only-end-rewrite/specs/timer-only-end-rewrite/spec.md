## ADDED Requirements

### Requirement: Non-timer update SHALL stay update

When the intent rail is already update and the resolved event is not a timer (`event_type` is not `time`), the item operation MUST remain `update`. The system MUST NOT change that item to `create` because the utterance contains an end cue (such as 结束, 停了, or 好了) or because an end time is present or absent. A non-timer item that still arrives as `end` at persist time MUST be stored as `update`, not as a new record.

非计时且轨已是更新时 MUST 只走更新。结束词或有没有结束时间 MUST NOT 把它改成新建。

#### Scenario: Formula amount change with an end-like word

- **WHEN** 用户要修改配方奶一类非计时事件，轨已是更新，句子里含有「好了」或「结束」
- **THEN** 落库子操作 MUST 为 `update`，MUST NOT 为 `create` 或 `end`

#### Scenario: End leaked to persist

- **WHEN** 非计时事件的子操作在进入落库收集时仍是 `end`，且轨是更新
- **THEN** 收集结果 MUST 改成 `update`，MUST NOT 写成新建

### Requirement: Open-timer rewrite SHALL apply only to timer events

The rewrite that turns an `end` item into a create when no in-progress row exists MUST run only for timer leaves (`event_type=time`). Non-timer items MUST NOT be queried or rewritten by that path. For a timer leaf, an in-progress row MUST keep `end`, and the absence of an in-progress row MUST still allow the existing closed-interval create path.

没有进行中就改成补记，MUST 只发生在计时事件上。

#### Scenario: Timer still ends or backfills

- **WHEN** 计时事件子操作是 `end`，且当前没有进行中的同一事件
- **THEN** 系统 MUST 仍可按现有规则转成补记新建，或在有进行中时保持结束

#### Scenario: Non-timer skips the open check

- **WHEN** 非计时事件轨已是更新
- **THEN** 系统 MUST NOT 因查不到进行中记录而把该子项改成 `create`

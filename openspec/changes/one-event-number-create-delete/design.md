## Context

`collect_event_items` 把句子里的 `quantity` 写成 batch 的 `eventNumber`，缺省为 0。字典叶子有 `one`、`number`、`time` 三种，字段可能在 `type` 或 `event_type`。`one` 表示一次一件，没有毫升或次数。计时事件补记闭合时，动作名也会是 `one`，那是 `action`，不是字典类型。

修改在选中历史行后，若 `eventNumber` 为空或 0，会抄那一行上的数。

## Goals / Non-Goals

**Goals:**

- `one` 类叶子在新增和删除的落库项上，`eventNumber` 为 1。
- `number` 仍用数量；`time` 不改。
- 修改继续抄历史行。

**Non-Goals:**

- 不改数量解析，不为 `one` 类追问数量。
- 不改 `time` 开表、结束、补记的时长字段。
- 不回写已经落库、`eventNumber` 为 0 的旧记录。

## Decisions

1. **只认字典类型。** 叶子的 `type` 或 `event_type`（去空白、小写）为 `one` 才改。`action=one` 的计时补记不改。
2. **只改增和删。** 子操作是 `create` 或 `delete` 时，在写入 `eventNumber` 之前把数量定为 1，盖过句子里偶然解析出的数。`update` 和 `end` 保持现有赋值；`end` 只出现在计时事件上。
3. **落点在组 batch。** 放在 `collect_event_items`，不在段解析里填一个假数量。这样删除叶子停掉数量解析之后，删除项仍是 1。

## Risks / Trade-offs

- [句子里对 `one` 类说了「两次」] → 仍写成 1。`one` 类一次一件，次数不走 `eventNumber`。
- [历史行上的 `one` 类记录仍是 0] → 本变更不迁移旧数据。新的删除请求带 1，选行仍按事件 id 和定位策略。

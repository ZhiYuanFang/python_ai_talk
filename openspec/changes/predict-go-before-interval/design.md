## Context

`speak_predict` 只有「何时」且 `time_answer` 为 `clock` 或 `remain` 时才打 Go。`active` 读 `expectEndAt`，`next` 读 `nextAt`，命中后用模板句。用量和用时直接进冷路径：近 7 日历史加本地间隔算法，再交给预测模型。

「这次要睡多久」的本地规则是通道 `next`、格子 `duration`、`time_answer` 为空，因此不会打 Go。imminent 的注释写明条目里还有 `expect*`，当前解析没用。本地算法按根汇总，睡眠的工具结果里会出现别的叶子的用量。

## Goals / Non-Goals

**Goals:**

- 何时、用量、用时都先向 Go 要本轮这一格。
- 这一格有数就播报，不再拉近 7 日。
- 没有条目、该格为空或接口失败时，保持现有间隔算法。

**Non-Goals:**

- 不改「还要多久」的何时模板，不把它改成念预计总时长。
- 不改预约约定接口。
- 不改兜底回答补快照。
- 不把 Go 的数写入间隔算法快照。

## Decisions

1. **按通道选接口。** `next` 打 imminent/pending，`active` 打 active-eta。匹配仍按叶子 id、根 id，与现有 `nextAt` / `expectEndAt` 对齐方式相同。「这次要睡多久」是 `next`，只打 imminent。
2. **只取本轮格子。** 何时继续用 `nextAt` 或 `expectEndAt` 和现有模板。用时读预计时长（秒），用量读预计用量。同一条上另一个数不拿来顶替。问用时而 Go 只有用量时，视为这一格没有，转入间隔算法。
3. **字段名兼容 camel 与 snake。** 时长依次看 `expectDurationSec`、`expect_duration_sec`、`expectDuration`。用量依次看 `expectAmount`、`expect_amount`。0 或空当没有。
4. **失败再兜底。** 接口异常、列表为空、对不上事件、该格没有数，都进入现有 `_resolve_tool_result` 间隔计算。预约事件不进这两路，仍走约定接口。
5. **Go 命中不写间隔快照。** 这一轮用 Go 的数回答即可。间隔快照仍只在本地算法 `status=ok` 时写入。

## Risks / Trade-offs

- [Go 字段名与上面三个不一致] → 实现时按真实条目补别名，不猜一个不存在的键去挡兜底。
- [imminent 的预计时长是下一次，不是当前这觉还剩多久] → 「这次要睡多久」本来就是下一次；进行中的剩余仍由「还要多久」走 `expectEndAt`。
- [Go 与本地算法数字不同] → 以 Go 为准。本地只在 Go 这一格缺失时出现。

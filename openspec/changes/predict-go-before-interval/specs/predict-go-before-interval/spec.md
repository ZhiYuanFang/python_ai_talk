## ADDED Requirements

### Requirement: 预测先读 Go 的本轮格子

当预测通道为 `next` 或 `active`，且不是预约事件时，系统 MUST 先请求 Go：`next` 使用 imminent/pending，`active` 使用 active-eta。系统 MUST 按事件 id 匹配条目，并只读取本轮格子对应的数：何时用 `nextAt` 或 `expectEndAt`，用时用预计时长，用量用预计用量。该格有有效数字时，系统 MUST 用这个数播报，且 MUST NOT 再拉取近 7 日历史。

#### Scenario: 这次要睡多久命中预计时长

- **WHEN** 用户说「这次要睡多久」，通道为 `next`，且 imminent 中睡眠条目带有预计时长
- **THEN** 系统用该预计时长回答，且不调用近 7 日间隔算法

#### Scenario: 何时仍用模板

- **WHEN** 用户问下一次何时，且 Go 返回了 `nextAt` 或 `expectEndAt`
- **THEN** 系统仍用现有时间点模板播报

### Requirement: Go 这一格没有时走间隔算法

Go 接口失败、没有匹配条目，或匹配条目上没有本轮格子的数时，系统 MUST 使用现有近 7 日间隔算法。系统 MUST NOT 用同一条上另一种数代替所问的格子。预约事件 MUST 仍走约定接口。

#### Scenario: 没有预计时长

- **WHEN** imminent 对上了睡眠，但该条目没有预计时长
- **THEN** 系统改走近 7 日间隔算法

#### Scenario: 还要多久不念总时长

- **WHEN** 用户问「还要多久」且 Go 给出了结束时间
- **THEN** 系统按剩余时间播报，不用预计总时长替换

### Requirement: Go 命中不写入间隔快照

使用 Go 返回的数完成本轮预测时，系统 MUST NOT 把该结果写入间隔算法快照。间隔快照 MUST 仍只在本地算法成功时写入。

#### Scenario: 用 Go 时长回答

- **WHEN** 本轮用时来自 Go 的预计时长
- **THEN** 间隔算法快照不被这次结果覆盖

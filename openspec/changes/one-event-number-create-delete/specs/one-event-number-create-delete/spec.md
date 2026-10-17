## ADDED Requirements

### Requirement: one 类增删的 eventNumber 为 1

当字典叶子的 `type` 或 `event_type` 为 `one`，且子操作为新增或删除时，系统 MUST 将该落库项的 `eventNumber` 设为 1。系统 MUST NOT 因句子里没有数量而写成 0，也 MUST NOT 采用句子里解析出的其它数量。

#### Scenario: 新增 one 类

- **WHEN** 用户记一笔字典类型为 `one` 的事件，且句子里没有数量
- **THEN** 落库项的 `eventNumber` 为 1

#### Scenario: 删除 one 类

- **WHEN** 用户删除字典类型为 `one` 的事件
- **THEN** 落库项的 `eventNumber` 为 1

### Requirement: number 与 time 以及修改保持原数量

`number` 类事件的 `eventNumber` MUST 仍为解析出的数量。`time` 类事件 MUST 保持现有赋值，包括动作名为 `one` 的计时补记。修改 MUST 继续使用选中历史行上的 `eventNumber`，MUST NOT 强制写成 1。

#### Scenario: 配方奶仍用毫升

- **WHEN** 用户记录 `number` 类事件且数量为 120
- **THEN** 落库项的 `eventNumber` 为 120

#### Scenario: 修改不强制为 1

- **WHEN** 用户修改一条已有记录
- **THEN** 落库项的 `eventNumber` 来自该历史行，而不是固定 1

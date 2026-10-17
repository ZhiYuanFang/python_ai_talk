## ADDED Requirements

### Requirement: Parent point query picks the leaf with the latest start

当本段是查记录点查且事件为父节点时，系统 MUST 在该父的全部可落库子孙叶子中选定一个叶子，且 MUST NOT 为此调用猜叶子模型。系统 MUST 为每个叶子取其开始时间最近的一条历史，再选取这些条里开始时间最大的叶子。开始时间相同则 MUST 选取子孙列表中更靠前的叶子。选中结果 MUST 视为历史选定，不得把整句写入该叶子的说法飞轮。

#### Scenario: Latest child record becomes the event

- **WHEN** 用户点查「上一次喂养是什么时候」，喂养是父事件，其子事件中配方奶的最近开始时间晚于其它子事件
- **THEN** 本轮事件 MUST 定为配方奶
- **AND** MUST NOT 调用猜叶子模型

### Requirement: No child history asks for the event name

当这些子孙叶子在本次拉取中都没有历史记录时，系统 MUST 打断并确认，问句 MUST 只列出子事件名。系统 MUST NOT 继续播报，也 MUST NOT 调用猜叶子模型。父下没有子孙叶子时 MUST 保持原有未识别结果。

#### Scenario: Empty child history asks by name

- **WHEN** 用户点查父事件「喂养」，其子孙叶子在历史中都没有记录，叶子名为配方奶、母乳、辅食
- **THEN** 系统 MUST 向用户确认，问句包含这些叶子名
- **AND** MUST NOT 调用猜叶子模型

### Requirement: Non-point parent resolution stays unchanged

父事件出现在记一笔、修改、删除，或事件仍未识别、存在多个消歧候选时，系统 MUST 保持原有猜测或确认路径。

#### Scenario: Unresolved event still uses the existing guess

- **WHEN** 点查句子没有命中任何事件名
- **THEN** 系统 MUST 继续原有的未识别猜测路径

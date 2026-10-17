## ADDED Requirements

### Requirement: 一次性事件回执不念数量

叶子类型为 `one` 时，入库成功回执 MUST NOT 包含 `eventNumber`。新增 MUST 形如「已记录{事件名}。」，修改 MUST 形如「已修改{事件名}。」。计量事件的回执 MUST 仍带数量和单位。发给 Go 的 `eventNumber` MUST 保持现状，`one` 的新增和删除仍为 1。

#### Scenario: 尿尿新增不说 1

- **WHEN** 用户说「尿尿了」，叶子类型为 `one`，入库成功且 `eventNumber` 为 1
- **THEN** 回执 MUST 为「已记录尿尿。」
- **THEN** 回执 MUST NOT 包含「1」

#### Scenario: 配方奶仍报用量

- **WHEN** 计量事件新增成功，数量为 120，单位为 ml
- **THEN** 回执 MUST 包含「120」和单位

#### Scenario: 修改一次性事件不说数量

- **WHEN** 修改一个类型为 `one` 的事件且入库成功
- **THEN** 回执 MUST 为「已修改{事件名}。」
- **THEN** 回执 MUST NOT 拼接 `eventNumber`

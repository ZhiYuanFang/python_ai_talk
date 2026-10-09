## ADDED Requirements

### Requirement: 缓存串台不得用错误 history_mode 播报查史
系统 MUST NOT 在意图缓存误命中（原文为区间次数/汇总而载荷为点查，或原文为上一次/什么时候而载荷为 daily）时，用错误模板向用户播报查史结果。此类冲突 MUST 在播报前被拒命中并回落分类，使得「今天喝水几次」类问法不会仅因向量近邻「上一次喝水…」而走点查或错误 mode。

#### Scenario: 几次问法不因近邻上一次而点查播报
- **WHEN** 用户问「今天喝水几次」
- **AND** 缓存近邻为上一次点查类喝水条目
- **THEN** 系统 MUST NOT 仅用该点查载荷完成播报
- **AND** SHALL 经分类（或门闩拒命中后的等价路径）再决定 `history_mode`

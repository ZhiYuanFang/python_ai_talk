## REMOVED Requirements

### Requirement: 时间维禁止向量飞轮
**Reason**: 改为相对配方时间飞轮（纯 A）；绝对 Unix 禁作主缓存，由 `intent-time-relative-flywheel` 约束。  
**Migration**: 使用时间整段飞轮 + 物化；保留 rule_gap。

## ADDED Requirements

### Requirement: 时间层纳入分层飞轮
系统 SHALL 将时间整段飞轮（相对配方）纳入分层飞轮清单，与 OP、事件、数量、R 子维、定位等隔离。时间层 payload MUST 为相对配方，MUST NOT 以绝对 Unix 为主缓存。

#### Scenario: 清单含时间层
- **WHEN** 描述或实现分层飞轮集合
- **THEN** SHALL 包含时间层（相对配方）
- **AND** 该层 MUST NOT 以绝对 Unix 对作为权威载荷

### Requirement: 热路径可含时间飞轮
当某段所需飞轮层（含时间相对配方层）均合法命中且物化成功时，系统 SHOULD 不调用对应维小 LLM（含 TIME LLM）即可完成该段主路径中的时间槽填充。规则已完整抽出时间时 MAY 不读时间飞轮。

#### Scenario: 时间飞轮齐备跳过 TIME LLM
- **WHEN** create 段规则未抽出时间，但时间飞轮命中合法配方并物化成功
- **THEN** 系统 MUST NOT 为此再调用 TIME 小 LLM

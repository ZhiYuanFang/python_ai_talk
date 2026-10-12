## REMOVED Requirements

### Requirement: 时间维保持无飞轮特例
**Reason**: 时间维纳入与其它维同构的飞轮路径（相对配方）。  
**Migration**: 使用 `resolve_time`：规则 → 飞轮 → LLM → 配方回写；rule_gap 保留。

## ADDED Requirements

### Requirement: 时间维同构 resolve（相对配方）
系统 SHALL 为时间维提供与其它飞轮维同构的解析入口，顺序为：本地规则 → 整段时间飞轮（相对配方物化）→ TIME 小 LLM → 成功且配方合法则以段整句回写。缺槽或解析失败 MUST NOT 写入时间飞轮。时间维 MUST NOT 因「其它维飞轮已命中」而跳过规则不足且无线索飞轮命中时的 TIME LLM。

#### Scenario: 时间飞轮命中跳过 TIME LLM
- **WHEN** 段原文命中时间飞轮且相对配方合法并物化成功
- **THEN** 系统 SHALL 采用物化后的起止时间
- **AND** MUST NOT 为此再调用 TIME 小 LLM

#### Scenario: 其它维命中不替代时间
- **WHEN** OP/数量等飞轮均已命中但时间规则未覆盖、时间飞轮未命中且存在时间线索
- **THEN** 系统 MAY 调用 TIME 小 LLM
- **AND** MUST 写入时间维 rule_gap（若调用了 LLM）

## REMOVED Requirements

### Requirement: 时间维继续规则缺口且不做时间飞轮
**Reason**: 保留时间规则缺口，但允许相对配方时间飞轮加速热路径。  
**Migration**: 见下方「时间维规则缺口与飞轮并存」。

## ADDED Requirements

### Requirement: 时间维规则缺口与飞轮并存
当时间维规则未覆盖并调用 TIME 小 LLM 时，系统 SHALL 写入规则缺口（`dimension=time`，`llm_used=true` 等既有字段约定）。时间相对配方飞轮 MAY 作为热路径加速；系统 MUST NOT 因存在时间飞轮而取消时间缺口机制。数量飞轮 MUST NOT 取消时间缺口机制。

#### Scenario: TIME LLM 仍进缺口箱
- **WHEN** 时间规则与时间飞轮均未满足后调用 TIME LLM
- **THEN** 规则缺口收件箱 SHALL 有对应 time 维记录

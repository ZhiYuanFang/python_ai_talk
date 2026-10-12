## ADDED Requirements

### Requirement: 时间维继续规则缺口且不做时间飞轮
当时间维规则未覆盖并调用 TIME 小 LLM 时，系统 SHALL 写入规则缺口（`dimension=time`，`llm_used=true` 等既有字段约定）。系统 MUST NOT 以时间向量飞轮替代缺口驱动的规则扩展。数量维 MAY 以数量飞轮为热路径主加速；数量规则 miss 时 MAY 仍写 quantity 缺口，但 MUST NOT 因数量飞轮而取消时间缺口机制。

#### Scenario: TIME LLM 仍进缺口箱
- **WHEN** 时间规则 miss 后调用 TIME LLM
- **THEN** 规则缺口收件箱 SHALL 有对应 time 维记录
- **AND** 系统 MUST NOT 要求存在时间向量集合才能完成该次解析

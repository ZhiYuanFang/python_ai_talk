## ADDED Requirements

### Requirement: SHAPE 纳入维级小 LLM 兜底族
系统 SHALL 将 SHAPE（计时开/关/补记）与 TYPE / EVENT / TIME / QTY 一并视为可按需调用的段维小 LLM 兜底能力。MUST NOT 因早期「SHAPE 仅推导」实现而拒绝在计时叶暧昧时调用 SHAPE 小 LLM。SHAPE 调用仍 MUST 遵守窄契约，MUST NOT 恢复满血多 events 分类。

#### Scenario: 五维均可兜底
- **WHEN** 计时叶形态规则无法裁定 start/end
- **THEN** 系统 SHALL 允许调用 SHAPE 小 LLM
- **AND** SHALL NOT 要求回退满血 classify 才能结束「睡醒了」类说法

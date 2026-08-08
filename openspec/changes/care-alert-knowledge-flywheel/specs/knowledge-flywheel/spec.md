## ADDED Requirements

### Requirement: Care-alert fixed intents update knowledge quality scores
系统 SHALL 允许护理留意固定意图反馈更新 `mother_baby_knowledge` 的质量分：`follow_up` 等价于正面反馈（quality_score 提升规则与 feedback=1 一致），`ignore` 等价于负面反馈（与 feedback=-1 一致）。更新 MUST 针对 analyze 阶段记录的知识文档 id；无 id 时 SHALL NOT 报错中断 ACK。

#### Scenario: follow_up updates like thumbs up
- **WHEN** care-alert feedback intent 为 follow_up 且存在关联 knowledge_ids
- **THEN** 系统对这些文档执行与 feedback=1 等价的质量分更新

#### Scenario: ignore updates like thumbs down
- **WHEN** care-alert feedback intent 为 ignore 且存在关联 knowledge_ids
- **THEN** 系统对这些文档执行与 feedback=-1 等价的质量分更新

## ADDED Requirements

### Requirement: Persona prompts apply to clinic only after tip removal

育儿专家人设与 grounded 提示词约定 SHALL 仅约束存活的 clinic（及共享会话续聊）路径。系统 MUST NOT 再要求 tip 开场提示词遵循原 tip 人格义务。

#### Scenario: No tip persona obligation

- **WHEN** tip agent 已删除
- **THEN** 不得再将 tip_answer system 作为验收对象

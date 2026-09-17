## ADDED Requirements

### Requirement: Grounded prompts without tip path

有据提示词约定 SHALL 适用于 clinic 等存活陪伴路径。系统 MUST NOT 再要求 tip 路径注入或点名历史的 tip 专用义务。

#### Scenario: Tip grounded path removed

- **WHEN** tip 已删除
- **THEN** grounded 规格验收 MUST NOT 依赖 tip_graph

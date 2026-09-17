## REMOVED Requirements

### Requirement: Standalone question rewrite for QA retrieval
**Reason**: clinic Q&A 捷径与问答飞轮整体删除。
**Migration**: clinic 一律走常规生成路径。

### Requirement: Global Q&A hit skips full clinic prepare
**Reason**: 不再维护全局 Q&A 向量捷径。
**Migration**: 无。

### Requirement: Promote accepted answers into Q&A store
**Reason**: 无隐式采纳飞轮，不再 promote。
**Migration**: 无。

### Requirement: Block fast path for history and sensitive cases
**Reason**: 快径已删除，禁入规则无意义。
**Migration**: 无。

## REMOVED Requirements

### Requirement: Judge previous suggestion before clinic reply
**Reason**: clinic 不再运行隐式采纳判定；通识/Q&A 飞轮已删，判定无产品用途。
**Migration**: 从 clinic 图移除 `implicit_feedback` 节点。

### Requirement: Tip opening counts as pending suggestion
**Reason**: 不再需要 tip 开场作为待飞轮建议。
**Migration**: tip 仍可写会话轮次，但不驱动飞轮。

### Requirement: Flywheel updates only on accept or reject
**Reason**: 通识质量飞轮删除。
**Migration**: 无。

### Requirement: Each suggestion judged at most once after successful classification
**Reason**: 隐式判定路径删除。
**Migration**: 无。

### Requirement: Explicit feedback endpoints remain available
**Reason**: 与基线后期 `retire-explicit-feedback` 及本变更冲突；显式 feedback 早已下线，本变更亦不恢复。
**Migration**: 无 clinic/tip `/feedback`；亦无隐式飞轮。

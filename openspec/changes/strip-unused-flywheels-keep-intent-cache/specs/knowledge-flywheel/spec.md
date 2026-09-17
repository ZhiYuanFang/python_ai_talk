## REMOVED Requirements

### Requirement: 向量库元数据扩展
**Reason**: 通识知识库与质量飞轮整体退役；不再维护 `mother_baby_knowledge` 元数据扩展义务。
**Migration**: 无；陪伴与护理留意不再检索通识库。

### Requirement: 用户反馈影响知识质量分
**Reason**: 通识质量飞轮删除；clinic/tip 不再隐式或显式更新通识分。
**Migration**: 无。

### Requirement: 定期清理低质量用户知识
**Reason**: 通识集合不再使用；定时任务仅保留意图缓存清理。
**Migration**: 保留 `feeding_intents` 低分清理，不得清通识。

### Requirement: 检索时优先匹配高质量知识
**Reason**: 通识检索路径删除。
**Migration**: clinic/tip 回答仅依赖画像、喂养史、会话与 LLM。

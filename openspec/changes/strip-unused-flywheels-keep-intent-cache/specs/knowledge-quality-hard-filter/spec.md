## REMOVED Requirements

### Requirement: Hard-filter knowledge by quality_score
**Reason**: clinic/tip 不再检索 `mother_baby_knowledge`，质量硬过滤无适用对象。
**Migration**: 删除 `search_vectors` 通识路径及质量过滤调用。

## ADDED Requirements

### Requirement: 意图缓存不得用本地查询句正则拦截
意图缓存命中判定 MUST 使用既有相似度与质量分门槛（及短窗重复扣分），MUST NOT 调用或依赖按用户原文匹配「上一次/什么时候」等词的本地函数来丢弃或改写命中结果。

#### Scenario: 不再因上一次丢掉 create 缓存
- **WHEN** 用户输入含「上一次」且意图缓存 Top-1 为 `op=create`、分数与质量分达标
- **THEN** 系统 SHALL 按缓存命中规则处理（命中则采用或按短窗扣分未命中）
- **AND** SHALL NOT 仅因原文含「上一次」而忽略该 create 缓存

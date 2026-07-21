## ADDED Requirements

### Requirement: 向量库元数据扩展
系统 SHALL 扩展 `mother_baby_knowledge` 向量库的元数据，包含 source、quality_score、match_count、helpful_count 等字段。

#### Scenario: 新上传的知识包含完整元数据
- **WHEN** 管理员上传新的 MD 文件
- **THEN** 向量库中的每条记录包含完整的扩展元数据

#### Scenario: 旧数据使用默认值
- **WHEN** 服务启动时检测到旧的向量记录
- **THEN** 系统自动为缺失字段填充默认值

### Requirement: 用户反馈影响知识质量分
系统 SHALL 根据用户反馈（👍/👎）更新知识的质量分数，👍提升质量分，👎降低质量分。

#### Scenario: 用户点赞提升质量分
- **WHEN** 用户对某个知识相关的回答点赞（feedback=1）
- **THEN** 该知识的 quality_score 增加 0.1，helpful_count 和 match_count 各增加 1

#### Scenario: 用户点踩降低质量分
- **WHEN** 用户对某个知识相关的回答点踩（feedback=-1）
- **THEN** 该知识的 quality_score 减少 0.2，match_count 增加 1

### Requirement: 定期清理低质量用户知识
系统 SHALL 每周执行一次清理任务，删除 source=user 且 quality_score < 0.3 的知识。

#### Scenario: 低质量知识被自动清理
- **WHEN** 定时任务执行时发现 source=user 且 quality_score < 0.3 的知识
- **THEN** 系统删除这些知识及其向量

#### Scenario: 管理员上传的知识不会被自动清理
- **WHEN** 定时任务执行时发现 source=admin 的知识（无论质量分）
- **THEN** 系统保留这些知识，不进行自动删除

### Requirement: 检索时优先匹配高质量知识
系统 SHALL 在向量检索时，将质量分作为权重因子，优先返回高质量知识。

#### Scenario: 高质量知识优先匹配
- **WHEN** 用户发起检索请求
- **THEN** 系统返回的结果中，高质量知识（quality_score > 0.8）排在前面

### Requirement: 知识匹配次数统计
系统 SHALL 在每次检索时，增加被匹配知识的 match_count。

#### Scenario: 知识被匹配后计数增加
- **WHEN** 用户检索到某个知识并用于生成回答
- **THEN** 该知识的 match_count 增加 1

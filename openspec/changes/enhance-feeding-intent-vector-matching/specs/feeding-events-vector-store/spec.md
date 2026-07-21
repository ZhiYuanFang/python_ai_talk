## ADDED Requirements

### Requirement: 系统创建独立的喂养事件向量库
系统 SHALL 创建独立的 `feeding_events` Collection，与 `mother_baby_knowledge` 物理隔离。

#### Scenario: 创建独立 Collection
- **WHEN** 系统启动
- **THEN** 创建或获取 `feeding_events` Collection
- **AND** 与 `mother_baby_knowledge` 物理隔离

### Requirement: 系统在事件字典更新时同步向量库
系统 SHALL 在事件字典缓存更新时（24小时TTL过期），自动检测变化并同步更新向量库中的standard数据。

#### Scenario: 新增事件同步
- **WHEN** 事件字典新增事件"洗澡"
- **THEN** 系统将"洗澡"添加到向量库
- **AND** 添加动作变体"开始洗澡"、"结束洗澡"、"记录洗澡"

#### Scenario: 修改事件名称同步
- **WHEN** 事件字典中"母乳"修改为"母乳喂养"
- **THEN** 系统更新向量库中对应的事件名称
- **AND** 保留用户表达记录

#### Scenario: 修改从属关系同步
- **WHEN** 事件"奶粉"的parent_id从1修改为2
- **THEN** 系统更新向量库中对应的parent_id字段

#### Scenario: 删除事件同步
- **WHEN** 事件字典删除事件"游泳"
- **THEN** 系统从向量库中删除对应的standard数据
- **AND** 删除关联的用户表达记录

### Requirement: 系统在服务启动时初始化喂养事件向量库
系统 SHALL 在服务启动时，从事件字典初始化喂养事件向量库。

#### Scenario: 启动时初始化
- **WHEN** 服务首次启动
- **AND** 向量库为空
- **THEN** 系统获取事件字典
- **AND** 将所有标准事件添加到向量库
- **AND** 添加动作变体

### Requirement: 系统支持置信度≥90%但用户否定时删除向量数据
系统 SHALL 在置信度≥90%但用户否定时，删除对应的向量数据（用户表达）。

#### Scenario: 删除错误匹配的向量数据
- **WHEN** 向量匹配置信度为93%
- **AND** 用户否定匹配结果
- **THEN** 系统删除该向量数据
- **AND** 不删除standard数据

### Requirement: 系统支持向量数据的CRUD操作
系统 SHALL 支持喂养事件向量数据的添加、查询、更新和删除操作。

#### Scenario: 添加向量数据
- **WHEN** 用户确认LLM解析意图正确
- **THEN** 系统添加用户表达到向量库

#### Scenario: 查询向量数据
- **WHEN** 用户输入需要匹配
- **THEN** 系统在向量库中查询相似事件

#### Scenario: 更新向量数据
- **WHEN** 用户确认向量匹配结果正确
- **THEN** 系统更新成功计数

#### Scenario: 删除向量数据
- **WHEN** 用户否定高置信度匹配结果
- **THEN** 系统删除对应的向量数据

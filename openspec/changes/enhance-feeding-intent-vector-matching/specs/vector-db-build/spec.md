## MODIFIED Requirements

### Requirement: 系统构建向量数据库
系统 SHALL 构建Chroma向量数据库，将母婴知识文档和喂养事件转换为向量并存储。

#### Scenario: 构建母婴知识向量库
- **WHEN** Docker构建阶段执行构建脚本
- **THEN** 加载data/knowledge目录下的文档
- **AND** 切分文档为chunks
- **AND** 将chunks转换为向量并存储到`mother_baby_knowledge` Collection

#### Scenario: 构建喂养事件向量库
- **WHEN** 服务启动时初始化
- **THEN** 获取事件字典
- **AND** 将标准事件名和动作变体转换为向量
- **AND** 存储到`feeding_events` Collection

#### Scenario: Docker构建阶段自动构建
- **WHEN** 构建Docker镜像
- **THEN** 自动执行构建脚本
- **AND** 将向量数据库打包进镜像

#### Scenario: 首次启动时自动构建
- **WHEN** 服务首次启动
- **AND** 向量数据库为空
- **THEN** 自动构建向量数据库
- **AND** 确保服务正常启动

#### Scenario: 增量更新
- **WHEN** 事件字典更新
- **THEN** 系统检测变化
- **AND** 增量更新喂养事件向量库
- **AND** 不影响母婴知识向量库

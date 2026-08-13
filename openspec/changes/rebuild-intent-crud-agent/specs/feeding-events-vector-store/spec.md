## REMOVED Requirements

### Requirement: 系统创建独立的喂养事件向量库
**Reason**: 意图飞轮改为独立 Collection `feeding_intents`；事件名空间 `feeding_events` 不再使用。
**Migration**: 停止创建/获取 `feeding_events`；磁盘残留可运维删除，不得误删 `mother_baby_knowledge` 或 `feeding_intents`。

### Requirement: 系统在事件字典更新时同步向量库
**Reason**: 不再维护标准事件名 + 动作变体向量。
**Migration**: `event_cache` 更新字典时 MUST NOT 再调用 `EventVectorStore.sync_events` / `initialize_events`。

### Requirement: 系统在服务启动时初始化喂养事件向量库
**Reason**: 启动不再构建事件名向量。
**Migration**: `main.py` 与 `scripts/build_vector_db.py` MUST NOT 再初始化 `feeding_events`。知识库构建保持原职责。

### Requirement: 系统支持置信度≥90%但用户否定时删除向量数据
**Reason**: 不再有事件名用户表达向量可删。
**Migration**: 无。

### Requirement: 系统支持向量数据的CRUD操作
**Reason**: `EventVectorStore` 整模块删除。
**Migration**: 意图缓存的增查由 `intent-cache-flywheel` 约定。

## ADDED Requirements

### Requirement: 拆除 feeding_events 存储与同步
系统 MUST 删除喂养事件名向量存储实现（`EventVectorStore` / `event_vector_store.py` 或等价）。服务启动、事件字典刷新与构建脚本 MUST NOT 再创建、初始化或同步 Chroma `feeding_events`。系统 MUST NOT 将事件字典标准名或动作变体写入任何仍命名为 `feeding_events` 的集合。知识库 Collection 与意图缓存 `feeding_intents` MUST NOT 因本条被删除或清空。

#### Scenario: 启动不再建 feeding_events
- **WHEN** 服务启动且事件字典可获取
- **THEN** 系统 SHALL NOT 创建或填充 `feeding_events`
- **AND** SHALL 仍可初始化知识库向量（若该路径需要）

#### Scenario: 字典变更不同步事件名向量
- **WHEN** 事件字典新增或改名叶子事件
- **THEN** 系统 SHALL 更新内存/缓存中的事件字典供分类提示使用
- **AND** SHALL NOT 向 `feeding_events` 写入标准条目或动作变体

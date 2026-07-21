## Why

当前喂养意图识别使用简单的关键词包含判断，缺乏语义理解能力，容易误判（如"奶粉喂养知识"被误判为"奶粉喂养"记录事件）。需要引入向量数据库进行语义相似度匹配，提升意图识别准确性，并通过用户反馈实现数据飞轮，持续优化匹配效果。同时需要对代码进行模块化重构，将喂养动作和喂养建议代码分离，便于问题追溯和维护。

## What Changes

- **新增喂养事件向量库**：创建独立的 `feeding_events` Collection，与母婴知识向量库物理隔离，避免数据紊乱
- **向量匹配前置判断**：在 LLM 分类前进行向量匹配，置信度≥95%直接判定，90%-95%需要用户确认，<90%走 LLM 分类
- **用户确认机制**：使用 LangGraph interrupt 能力，在喂养意图落库前询问用户确认
- **数据飞轮机制**：用户确认 LLM 解析正确后，将用户表达添加到向量库，提升后续匹配能力
- **错误处理**：置信度≥90%但用户否定时，删除对应的向量数据，避免再次错误匹配
- **事件字典自动同步**：事件字典每24小时更新时，自动同步更新向量库中的 standard 数据
- **代码模块化重构**：将喂养动作和喂养建议代码分离到独立文件夹，便于问题追溯
- **代码注释规范**：制定全局代码注释规范，确保每行关键业务逻辑都有中文注释

## Capabilities

### New Capabilities

- `feeding-intent-vector-matching`: 喂养意图向量匹配能力，使用语义相似度进行事件识别
- `feeding-intent-user-confirmation`: 喂养意图用户确认机制，使用 LangGraph interrupt 实现
- `feeding-intent-data-flywheel`: 喂养意图数据飞轮，通过用户反馈持续优化向量库
- `feeding-events-vector-store`: 喂养事件向量库管理，包含独立 Collection 和自动同步机制
- `code-organization-standard`: 代码组织规范，分离喂养动作和喂养建议代码

### Modified Capabilities

- `intent-analysis`: 意图分析能力，新增向量匹配前置判断流程
- `vector-db-build`: 向量数据库构建能力，新增喂养事件向量库构建流程

## Impact

- **代码结构**：重构 `app/` 目录，新增 `app/feeding/` 和 `app/clinic/` 模块
- **向量数据库**：新增 `feeding_events` Collection
- **API 接口**：修改 `/v1/analyze/intent` 接口，支持用户确认流程
- **事件缓存**：增强 `EventCache`，支持向量库同步
- **构建脚本**：扩展 `build_vector_db.py`，支持喂养事件向量库构建
- **Docker 构建**：修改 `Dockerfile`，添加向量库自动构建步骤

## ADDED Requirements

### Requirement: Intent cache is the sole data flywheel

系统 SHALL 将喂养意图缓存（Chroma 集合 `feeding_intents`：确认且落库成功后写入整份 CRUD 意图、图入口匹配命中、质量分与定时低分清理）作为仓库唯一保留的数据飞轮。系统 MUST NOT 再维护通识知识质量飞轮、Q&A 捷径飞轮或 care_alert prompt 对比样例飞轮。意图缓存清理与检索 MUST NOT 修改或依赖 `mother_baby_knowledge` / `qa_fast_path` 集合。

#### Scenario: Intent cache match still available

- **WHEN** 用户重复一句已成功缓存的独立喂养意图表述且相似度与质量门槛满足
- **THEN** 意图图入口 MAY 命中缓存并跳过或缩短分类路径（与既有意图缓存行为一致）

#### Scenario: No cross-writes to retired collections

- **WHEN** 意图缓存写入或定时清理执行
- **THEN** 系统 MUST NOT 更新 `mother_baby_knowledge` 或 `qa_fast_path` 文档

## 1. 代码重构：目录结构

- [x] 1.1 创建 `app/feeding/` 目录结构（graphs/nodes、graphs/states、schemas、services）
- [x] 1.2 创建 `app/clinic/` 目录结构（graphs/nodes、graphs/states、schemas、services）
- [x] 1.3 创建 `app/shared/` 目录，迁移共享服务（http_client、llm_client、redis_gate）
- [x] 1.4 迁移喂养动作相关代码到 `app/feeding/`（intent_graph、classify_intent、intent_state、intent schema）
- [x] 1.5 迁移喂养建议相关代码到 `app/clinic/`（clinic_graph、tip_graph、clinic_state、tip_state、tip schema）
- [x] 1.6 更新 `app/main.py`，导入新目录结构的模块
- [x] 1.7 更新 `app/api/routes/`，按功能模块组织路由
- [x] 1.8 创建 `docs/coding-standard.md`，制定全局代码注释规范

## 2. 向量库增强：喂养事件向量库

- [x] 2.1 修改 `app/feeding/services/event_vector_store.py`，创建独立的 `feeding_events` Collection
- [x] 2.2 实现向量数据的 CRUD 操作（add、search、update、delete）
- [x] 2.3 实现向量数据质量评分和清理机制
- [x] 2.4 修改 `app/services/event_cache.py`，支持事件字典更新时同步向量库
- [x] 2.5 实现事件字典变化检测（新增、修改、删除）
- [x] 2.6 实现标准事件动作变体生成（开始、结束、记录）
- [x] 2.7 扩展 `scripts/build_vector_db.py`，支持喂养事件向量库构建
- [x] 2.8 实现服务启动时自动初始化喂养事件向量库

## 3. 意图分析增强：向量匹配和用户确认

- [x] 3.1 创建向量匹配节点 `app/feeding/graphs/nodes/match_event_by_vector.py`
- [x] 3.2 实现置信度分层判定逻辑（≥95%直接判定、90%-95%需要确认、<90%走LLM）
- [x] 3.3 创建确认话术生成节点 `app/feeding/graphs/nodes/prepare_confirm.py`
- [x] 3.4 创建用户反馈处理节点 `app/feeding/graphs/nodes/handle_feedback.py`
- [x] 3.5 实现数据飞轮逻辑（用户确认LLM解析后添加用户表达）
- [x] 3.6 实现错误处理逻辑（置信度≥90%但用户否定时删除向量数据）
- [x] 3.7 修改 `app/feeding/graphs/intent_graph.py`，添加向量匹配和确认流程
- [x] 3.8 配置 LangGraph interrupt 机制
- [x] 3.9 更新 `app/feeding/graphs/states/intent_state.py`，扩展状态字段
- [x] 3.10 更新 `app/feeding/schemas/intent.py`，添加确认相关字段

## 4. 部署配置：Docker和构建

- [x] 4.1 修改 `Dockerfile`，添加向量库自动构建步骤
- [x] 4.2 更新 `docker-compose.yml`，添加向量数据库 volume 挂载
- [x] 4.3 更新 `docker-compose.local.yml`，适配新的目录结构
- [x] 4.4 更新 `docker-compose.prod.yml`，适配新的目录结构
- [x] 4.5 更新 `docker-compose.test.yml`，适配新的目录结构
- [x] 4.6 更新 `.github/workflows/docker-acr.yml`，适配新的构建流程

## 5. 测试和验证

- [x] 5.1 创建喂养动作模块测试 `tests/test_feeding/`
- [x] 5.2 创建喂养建议模块测试 `tests/test_clinic/`
- [x] 5.3 创建向量匹配测试用例
- [x] 5.4 创建用户确认流程测试用例
- [x] 5.5 创建数据飞轮测试用例
- [x] 5.6 运行所有测试，确保通过

## 6. 文档更新

- [x] 6.1 更新 `docs/deploy-guide.md`，添加新的部署说明
- [x] 6.2 更新 `docs/vector_db_guide.md`，添加喂养事件向量库说明
- [x] 6.3 更新 `README.md`，说明新的目录结构和功能

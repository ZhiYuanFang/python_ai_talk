## 1. Python 服务端 - 向量库元数据扩展

- [ ] 1.1 修改 `app/shared/vector_store.py`，扩展向量库元数据字段（source、quality_score、match_count、helpful_count、category、doc_id、file_name、created_at、updated_at、chunk_index、total_chunks）
- [ ] 1.2 修改 `scripts/build_vector_db.py`，构建时添加扩展元数据
- [ ] 1.3 添加服务启动时旧数据元数据补全逻辑

## 2. Python 服务端 - 知识库管理 API

- [ ] 2.1 创建 `app/api/routes/knowledge.py`，实现 `/v1/knowledge/upload` 接口（支持 MD 文件上传、切分、Embedding、写入向量库）
- [ ] 2.2 实现 `/v1/knowledge/list` 接口（支持分页和分类筛选）
- [ ] 2.3 实现 `/v1/knowledge/{doc_id}` GET 接口（获取文档详情）
- [ ] 2.4 实现 `/v1/knowledge/{doc_id}` PUT 接口（更新文档内容并重建向量）
- [ ] 2.5 实现 `/v1/knowledge/{doc_id}` DELETE 接口（删除文档及其向量）
- [ ] 2.6 实现 `/v1/knowledge/stats` 接口（获取统计信息）
- [ ] 2.7 实现 `/v1/knowledge/categories` 接口（获取分类列表）
- [ ] 2.8 在 `app/api/routes/__init__.py` 中注册 knowledge_router

## 3. Python 服务端 - 反馈接口

- [ ] 3.1 在 `app/api/routes/tip.py` 中添加 `/v1/tip/feedback` 接口
- [ ] 3.2 创建 `app/api/routes/clinic.py`（如不存在），添加 `/v1/clinic/feedback` 接口
- [ ] 3.3 实现反馈频率限制逻辑（Redis 限流，同一 device_no 5 分钟内最多 3 次）

## 4. Python 服务端 - 知识飞轮逻辑

- [ ] 4.1 创建 `app/clinic/services/knowledge_vector_store.py`，实现质量分更新逻辑（👍提升/👎降低）
- [ ] 4.2 实现向量检索时 match_count 统计逻辑
- [ ] 4.3 实现检索结果按 quality_score 权重排序
- [ ] 4.4 实现定期清理任务（每周执行，删除 source=user 且 quality_score < 0.3 的知识）
- [ ] 4.5 修改 `app/clinic/graphs/nodes/search_vectors.py`，集成质量分统计和排序

## 5. Python 服务端 - Web 前端管理页面

- [ ] 5.1 创建 `web/` 目录，初始化 Vue 3 + Vite + Element Plus 项目
- [ ] 5.2 创建 `web/src/api/knowledge.js`，封装知识库 API 调用
- [ ] 5.3 创建 `web/src/components/KnowledgeList.vue`，实现文档列表组件
- [ ] 5.4 创建 `web/src/components/KnowledgeForm.vue`，实现上传/编辑表单组件
- [ ] 5.5 创建 `web/src/components/StatsCard.vue`，实现统计卡片组件
- [ ] 5.6 创建 `web/src/views/Dashboard.vue`，实现仪表盘页面
- [ ] 5.7 创建 `web/src/views/KnowledgeManage.vue`，实现知识管理页面
- [ ] 5.8 创建 `web/src/App.vue`，配置路由和布局
- [ ] 5.9 配置 `vite.config.js`，添加 proxy 代理后端 API
- [ ] 5.10 修改 `app/main.py`，注册静态文件托管（web/dist/）

## 6. Python 服务端 - 诊疗流式响应扩展

- [ ] 6.1 修改诊疗流式响应，在回答完成时发送 `{"type": "done", "answerId": <id>}` 事件
- [ ] 6.2 修改 `app/clinic/graphs/nodes/stream_response.py`，支持 done 事件输出

## 7. Python 服务端 - 配置和部署

- [ ] 7.1 修改 `Dockerfile`，添加前端构建步骤
- [ ] 7.2 修改 `.gitignore`，添加 `web/node_modules/` 和 `web/dist/`（开发环境）
- [ ] 7.3 更新 `docs/deploy-guide.md`，添加知识库管理和前端部署说明

## 8. Go 服务端 - TipStream 客户端

- [ ] 8.1 在 `internal/services/voice/python_ai_client.go` 中添加 `TipStream` 方法，调用 Python `/v1/tip/stream` 接口
- [ ] 8.2 添加 TipStream 调用点，在事件触发时调用小贴士生成

## 9. Go 服务端 - 反馈接口和数据库

- [ ] 9.1 创建 `clinic_session` 表（DAO/entity/migration）
- [ ] 9.2 创建 `tip_feedback` 表（DAO/entity/migration）
- [ ] 9.3 创建 `clinic_feedback` 表（DAO/entity/migration）
- [ ] 9.4 修改诊疗 WS 逻辑，回答完成时将会话落库并返回 answerId
- [ ] 9.5 创建 `/tip/feedback` 接口（API/controller/service）
- [ ] 9.6 创建 `/clinic/feedback` 接口（API/controller/service）
- [ ] 9.7 实现反馈同步到 Python 服务的逻辑

## 10. Flutter 客户端 - 诊疗反馈按钮

- [ ] 10.1 抽取 `FeedbackButtons` 公共组件（复用小贴士的反馈按钮 UI）
- [ ] 10.2 修改 `pangbao_ai_screen.dart`，在诊疗回答下方添加反馈按钮
- [ ] 10.3 在 `clinic_repository.dart` 中添加诊疗反馈 API 调用方法
- [ ] 10.4 实现诊疗反馈状态管理（每条回答独立的反馈状态）
- [ ] 10.5 实现反馈提交后的 UI 更新（按钮变灰、显示确认提示）

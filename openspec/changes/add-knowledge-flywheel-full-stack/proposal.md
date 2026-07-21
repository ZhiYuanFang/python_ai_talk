## Why

当前母婴知识库直接随代码发布，无法通过外部上传动态扩展；用户反馈机制缺失，无法实现知识质量的持续优化（数据飞轮）；诊疗回答没有反馈入口，无法收集用户对回答质量的评价。本变更旨在实现知识的动态管理和用户反馈闭环，构建完整的数据飞轮体系。

## What Changes

- 新增知识库管理 API，支持外部上传 MD 文件动态扩展知识库
- 新增向量库元数据扩展（source、quality_score、match_count、helpful_count 等）
- 新增诊疗回答反馈机制（answerId + 👍/👎 反馈）
- 新增小贴士反馈接口，完成反馈闭环
- 新增知识飞轮逻辑（反馈影响质量分、定期清理低质量知识）
- 新增 Vue 前端管理页面（独立 `web/` 目录，与服务端隔离）
- 修改 Go 侧 PythonAIClient，添加 TipStream 客户端
- 修改诊疗 WS 协议，回答完成时返回 answerId

## Capabilities

### New Capabilities

- `knowledge-management-api`: 知识库管理 API，支持 MD 文件上传、CRUD 操作
- `knowledge-flywheel`: 知识数据飞轮，包括反馈处理、质量评分、定期清理
- `clinic-feedback`: 诊疗回答反馈机制，支持 answerId 和用户反馈
- `tip-feedback`: 小贴士反馈机制，接收用户 👍/👎 反馈
- `knowledge-web-ui`: Vue 前端管理页面，提供知识库管理界面

### Modified Capabilities

- `clinic-stream`: 修改诊疗流式响应，新增 answerId 返回字段

## Impact

- **Python 服务**: 新增 `app/api/routes/knowledge.py`、`app/clinic/services/knowledge_vector_store.py`、`web/` 前端目录
- **Go 服务**: 修改 `internal/services/voice/python_ai_client.go`（新增 TipStream）、新增 `tip_feedback` 和 `clinic_feedback` 表
- **Flutter 客户端**: 修改 `pangbao_ai_screen.dart`（新增反馈按钮）
- **API 变更**: 新增 `/v1/knowledge/*`、`/v1/tip/feedback`、`/v1/clinic/feedback` 接口
- **数据库**: 向量库元数据扩展，新增质量评分字段

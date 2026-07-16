## Why

创建基于 LangGraph 框架的 Python AI 服务，替代 go_ai_talk 中的 LLM 调用逻辑，实现自然语言意图识别和母婴喂养建议功能。通过 Python 服务实现智能历史数据范围判断、向量检索增强、以及统一的 LLM 调用入口，提升母婴喂养场景的智能能力。

## What Changes

- **新建 Python 微服务**: 基于 FastAPI + LangGraph 框架，提供 HTTP 接口供 go_ai_talk 调用
- **替代 LLM 调用**: go_ai_talk 的 `callDeepSeekUnifiedIntent`、`callDeepSeekGrowthSuggestion`、`callDeepSeekHistoryReply`、`callDeepSeekDirectReply`、`handleIntentGeneral`、`streamClinicLLM` 改为调用 Python 服务
- **智能历史判断**: Python 服务根据用户输入自然语言智能判断需要拉取的历史数据范围，而非固定时间段
- **向量检索增强**: 新增 Chroma 向量数据库，用于母婴知识检索
- **流式诊疗支持**: 胖宝诊疗场景支持 SSE 流式响应
- **Docker 集成**: 创建 Dockerfile 和 docker-compose 配置，与 go_ai_talk 部署体系集成
- **CI/CD 自动化**: 创建 GitHub Actions 工作流，支持 tag 自动构建推送阿里云 ACR

## Capabilities

### New Capabilities

- `intent-analysis`: 语音喂养意图分析，识别用户输入的意图类型（start/end/one/search/suggest/conversation/exit），输出结构化 JSON
- `clinic-consultation`: 胖宝诊疗咨询，支持流式响应，结合历史数据和知识库给出诊疗建议
- `growth-suggestion`: 成长建议生成，基于历史喂养记录生成个性化建议
- `history-query`: 历史记录查询，根据用户问题智能检索相关历史记录
- `vector-db-build`: 向量数据库构建脚本，支持文档切分、embedding、写入 Chroma
- `vector-db-guide`: 向量数据库完整教学文档，从概念到使用的详细说明
- `docker-deployment`: Docker 部署配置，支持本地开发和生产部署
- `cicd-pipeline`: GitHub Actions CI/CD 流水线，支持自动构建推送阿里云 ACR

### Modified Capabilities

- *(go_ai_talk)* `voice-chat`: 修改 `callDeepSeekUnifiedIntent`、`callDeepSeekGrowthSuggestion`、`callDeepSeekHistoryReply`、`callDeepSeekDirectReply`、`handleIntentGeneral` 改为调用 Python 服务
- *(go_ai_talk)* `clinic-service`: 修改 `streamClinicLLM` 改为调用 Python 服务
- *(go_ai_talk)* `docker-compose`: 新增 python-ai-talk 服务配置

## Impact

### Python 项目 (新建)

- 新增服务端口: 8000
- 新增依赖: httpx, langgraph, langchain-openai, chromadb, sentence-transformers, cachetools, pydantic-settings
- 新增向量库: Chroma（持久化到 Volume）

### Go 项目 (修改)

- 修改文件: `internal/services/voice/voice_chat_understanding.go`, `internal/services/voice/voice_chat_deepseek.go`, `internal/services/voice/clinic_llm.go`
- 修改文件: `manifest/docker/docker-compose.microservices.yml`, `manifest/docker/docker-compose.microservices.prod.yml`, `manifest/docker/docker-compose.microservices.test.yml`, `manifest/docker/docker-compose.microservices.local.yml`
- 新增环境变量: `PYTHON_AI_TALK_URL`

### 部署体系

- 新增 Docker Volume: `chroma-data`, `embedding-models`
- 新增 ACR 镜像: `python-ai-talk`
- GitHub Actions Secrets: `ACR_USERNAME`, `ACR_PASSWORD`, `REGISTRY` (test/prod)
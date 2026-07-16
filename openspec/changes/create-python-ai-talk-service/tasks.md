## 1. 项目骨架和依赖配置

- [x] 1.1 创建项目目录结构（app/, scripts/, data/, tests/）
- [x] 1.2 创建 pyproject.toml，添加依赖（fastapi, uvicorn, httpx, langgraph, langchain-openai, chromadb, sentence-transformers, cachetools, pydantic-settings）
- [x] 1.3 创建 .gitignore 文件
- [x] 1.4 创建环境变量配置文件模板（.env.example）

## 2. 基础服务

- [x] 2.1 实现 LLM 客户端封装（支持 DeepSeek/Zhipu 双 provider），添加详细中文业务逻辑注释
- [x] 2.2 实现 HTTP 客户端（httpx，用于调用 go_ai_talk 兄弟仓 API），添加详细中文业务逻辑注释
- [x] 2.3 实现向量存储服务（Chroma + BGE-small-zh-v1.5），添加详细中文业务逻辑注释
- [x] 2.4 实现事件字典缓存（cachetools.TTLCache，24h TTL），添加详细中文业务逻辑注释
- [x] 2.5 实现 Redis 闸门控制（用于 LLM 并发控制），添加详细中文业务逻辑注释

## 3. 意图分析接口

- [x] 3.1 创建 FastAPI 应用主入口（app/main.py），添加详细中文业务逻辑注释
- [x] 3.2 实现意图分析接口 `/v1/analyze/intent`（POST），添加详细中文业务逻辑注释
- [x] 3.3 实现意图分类逻辑（调用 LLM 进行意图识别），添加详细中文业务逻辑注释
- [x] 3.4 实现智能历史数据范围判断，添加详细中文业务逻辑注释
- [x] 3.5 实现事件名称匹配（使用缓存的事件字典），添加详细中文业务逻辑注释
- [x] 3.6 实现对话意图处理（other 兜底文案），添加详细中文业务逻辑注释
- [x] 3.7 添加请求参数验证和错误处理，添加详细中文业务逻辑注释

## 4. 胖宝诊疗接口

- [x] 4.1 实现胖宝诊疗流式接口 `/v1/clinic/stream`（POST，SSE），添加详细中文业务逻辑注释
- [x] 4.2 实现向量检索增强（从 Chroma 检索相关母婴知识），添加详细中文业务逻辑注释
- [x] 4.3 实现历史数据获取（根据问题智能判断范围），添加详细中文业务逻辑注释
- [x] 4.4 实现宝宝画像获取（从 device-service 获取生日信息），添加详细中文业务逻辑注释
- [x] 4.5 实现流式 LLM 调用（支持 thinking 和 answer 双输出），添加详细中文业务逻辑注释
- [x] 4.6 添加请求参数验证和错误处理，添加详细中文业务逻辑注释

## 5. 向量库构建脚本

- [x] 5.1 创建向量库构建脚本（scripts/build_vector_db.py），添加详细中文业务逻辑注释
- [x] 5.2 实现文档加载功能（支持 Markdown/TXT 格式），添加详细中文业务逻辑注释
- [x] 5.3 实现中文文档切分（按句子边界，chunk 大小 512 tokens），添加详细中文业务逻辑注释
- [x] 5.4 实现 Embedding 功能（BGE-small-zh-v1.5），添加详细中文业务逻辑注释
- [x] 5.5 实现向量写入 Chroma 功能，添加详细中文业务逻辑注释
- [x] 5.6 实现增量更新支持（检测新增/更新文档），添加详细中文业务逻辑注释
- [x] 5.7 实现向量库验证功能（数量统计和检索测试），添加详细中文业务逻辑注释

## 6. 向量数据库教学文档

- [x] 6.1 创建向量数据库教学文档（docs/vector_db_guide.md），从基础概念开始讲解
- [x] 6.2 编写第一章：向量数据库基础概念（什么是向量数据库、为什么需要、与传统数据库区别）
- [x] 6.3 编写第二章：Embedding 概念（什么是 Embedding、文本转向量原理、BGE-small-zh-v1.5 介绍）
- [x] 6.4 编写第三章：Chroma 向量数据库（Chroma 介绍、核心概念、使用场景）
- [x] 6.5 编写第四章：环境准备（Python 安装、依赖安装、模型下载说明）
- [x] 6.6 编写第五章：知识库准备（文档格式、目录结构、示例文档）
- [x] 6.7 编写第六章：向量库构建（构建脚本使用、构建过程、结果验证）
- [x] 6.8 编写第七章：向量库使用（检索操作、参数说明、结果解析）
- [x] 6.9 编写第八章：向量库维护（增量更新、全量重建、备份恢复）
- [x] 6.10 编写第九章：常见问题解答（FAQ）
- [x] 6.11 提供示例知识库文档（data/knowledge/ 目录下）

## 7. Docker 部署配置

- [x] 7.1 创建 Dockerfile（多阶段构建，开发/生产镜像），添加详细中文业务逻辑注释
- [~] 7.2 在 go_ai_talk 的 docker-compose.microservices.yml 中新增 python-ai-talk 服务配置（go_ai_talk 不在工作目录，已在 python_ai_talk 中创建独立 docker-compose.yml）
- [~] 7.3 在 docker-compose.microservices.prod.yml 中新增 python-ai-talk 生产配置（go_ai_talk 不在工作目录）
- [~] 7.4 在 docker-compose.microservices.test.yml 中新增 python-ai-talk 测试配置（go_ai_talk 不在工作目录）
- [~] 7.5 在 docker-compose.microservices.local.yml 中新增 python-ai-talk 本地配置（go_ai_talk 不在工作目录）
- [x] 7.6 实现健康检查接口 `/health`，添加详细中文业务逻辑注释
- [x] 7.7 实现服务启动时自动构建向量库逻辑，添加详细中文业务逻辑注释

## 8. CI/CD 流水线

- [x] 8.1 创建 .github/workflows/docker-acr.yml 工作流文件
- [x] 8.2 实现 tag 触发构建逻辑（v* 格式）
- [x] 8.3 实现环境判断逻辑（rc/beta → test，纯数字 → prod）
- [x] 8.4 实现 ACR 登录步骤（使用 GitHub Secrets）
- [x] 8.5 实现 Docker 镜像构建步骤
- [x] 8.6 实现镜像推送步骤（多标签推送）
- [x] 8.7 实现手动触发支持（workflow_dispatch）
- [x] 8.8 实现构建取消逻辑（自动取消旧工作流）

## 9. go_ai_talk 修改

- [ ] 9.1 修改 `internal/services/voice/voice_chat_understanding.go` 中的 `callDeepSeekUnifiedIntent` 改为调用 Python 服务
- [ ] 9.2 修改 `callDeepSeekGrowthSuggestion` 改为调用 Python 服务
- [ ] 9.3 修改 `callDeepSeekHistoryReply` 改为调用 Python 服务
- [ ] 9.4 修改 `callDeepSeekDirectReply` 改为调用 Python 服务
- [ ] 9.5 修改 `handleIntentGeneral` 改为调用 Python 服务
- [ ] 9.6 修改 `internal/services/voice/clinic_llm.go` 中的 `streamClinicLLM` 改为调用 Python 服务
- [ ] 9.7 添加 `PYTHON_AI_TALK_URL` 环境变量配置

## 10. 测试和验证

- [x] 10.1 编写单元测试（意图分类、历史数据判断、向量检索），添加详细中文业务逻辑注释
- [x] 10.2 编写集成测试（API 接口测试），添加详细中文业务逻辑注释
- [~] 10.3 本地 Docker Compose 启动测试（需要实际运行环境）
- [~] 10.4 验证与 go_ai_talk 的兼容性（go_ai_talk 不在工作目录）
- [~] 10.5 性能测试（延迟和并发）（需要实际运行环境）
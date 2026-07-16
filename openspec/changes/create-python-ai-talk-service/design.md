## Context

当前 go_ai_talk 项目中的 LLM 调用逻辑（意图分析、成长建议、历史问答、胖宝诊疗）直接硬编码在 Go 代码中，使用 `aimodel.Invoke()` 和 `aimodel.InvokeStream()` 直接调用 DeepSeek/Zhipu API。这种架构存在以下问题：

1. **意图分析逻辑复杂**: 需要解析自然语言、匹配事件字典、判断 CRUD 操作，Go 代码难以维护
2. **历史数据范围固定**: 硬编码 12 小时/48 小时/7 天，无法根据用户问题动态调整
3. **缺乏向量检索能力**: 母婴知识体系无法有效利用
4. **代码重复**: 多个地方调用 LLM，逻辑分散
5. **扩展性差**: 新增意图类型或知识源需要修改 Go 代码并重新部署

为解决这些问题，设计基于 LangGraph 框架的 Python AI 服务，作为 go_ai_talk 的"智能内核"，提供统一的 LLM 调用入口和增强能力。

## Goals / Non-Goals

**Goals:**

1. 替代 go_ai_talk 中所有非流式 LLM 调用（意图分析、成长建议、历史问答、对话回复）
2. 替代 go_ai_talk 中流式 LLM 调用（胖宝诊疗）
3. 实现智能历史数据范围判断（根据自然语言动态决定拉取范围）
4. 实现向量检索增强（Chroma + BGE-small-zh-v1.5）
5. 保持与 go_ai_talk 的兼容性（返回相同的 JSON 结构）
6. 提供 Docker 部署和 CI/CD 自动化
7. 支持 DeepSeek/Zhipu 双模型切换（由 Go 传入配置）

**Non-Goals:**

1. 不替代 go_ai_talk 的 CRUD 操作（保留 Go 侧数据库操作）
2. 不替代 go_ai_talk 的闲聊流式模式（保留 Go 直连）
3. 不替代 go_ai_talk 的 TTS 功能（保留 Go 侧 TTS）
4. 不改变 go_ai_talk 的业务流程（只替换 LLM 调用部分）
5. 不实现用户认证（Python 服务为内部服务，无需认证）

## Decisions

### 1. 架构设计：Go 决策，Python 执行

**决策**: Go 侧保留所有业务逻辑（额度检查、降级判断、CRUD 操作），Python 侧只负责 LLM 调用和向量检索。

**理由**:
- Go 侧已有成熟的业务流程，改动最小化
- Python 侧专注于 AI 能力，职责单一
- Go 传入完整的 LLM 配置（provider + model + maxInFlight），Python 无需判断额度
- 兼容性保证：返回与 go_ai_talk `deepSeekUnifiedIntent` 相同的 JSON 结构

**替代方案**: Python 端处理完整业务流程 → 风险：改动大，可能引入兼容性问题

### 2. API 设计：统一入口 + 场景分离

**决策**: 提供统一的 `/v1/analyze/intent` 接口处理语音喂养场景，独立的 `/v1/clinic/stream` 接口处理胖宝诊疗场景。

**理由**:
- 语音喂养需要严格兼容 Go 的意图结构，接口设计固定
- 胖宝诊疗需要流式响应和向量检索，设计更灵活
- 场景分离便于独立优化和扩展

**替代方案**: 单一接口处理所有场景 → 风险：接口过于复杂，难以维护

### 3. 历史数据获取：Python 智能判断

**决策**: Python 服务根据用户输入自然语言智能判断历史数据范围，而非 Go 传入固定时间段。

**理由**:
- 用户可能问"今天吃了多少"（24小时）、"最近一周"（7天）、"上次"（1条）等不同范围的问题
- Python 可以根据关键词灵活调整，提升回答准确性
- 减少 Go 侧的数据处理负担

**替代方案**: Go 传入历史数据 → 风险：无法动态调整范围，灵活性差

### 4. 向量数据库：Chroma + BGE-small-zh-v1.5

**决策**: 使用 Chroma 作为向量数据库（本地持久化），BGE-small-zh-v1.5 作为 embedding 模型（本地下载）。

**理由**:
- Chroma 0 部署，开箱即用，适合新手
- BGE-small-zh-v1.5 中文效果好，体积小（~90MB），免费
- 本地部署，无需额外服务，降低运维成本

**替代方案**:
- Pinecone/Weaviate 云服务 → 成本高，网络延迟
- Milvus → 部署复杂
- Sentence-BERT → 效果不如 BGE

### 5. LLM 客户端：统一封装 + 闸门控制

**决策**: 封装统一的 LLM 客户端，支持 DeepSeek/Zhipu 双 provider，共享 Redis 闸门控制。

**理由**:
- 统一接口，便于切换 provider
- Redis 闸门控制与 Go 侧一致，避免超并发
- 根据 Go 传入的 provider/model 动态选择

**替代方案**: 分别封装不同 provider → 代码重复，维护成本高

### 6. 向量库构建：运行时挂载 Volume

**决策**: 向量库数据不打包进镜像，而是运行时通过 Volume 挂载，第一次启动时构建。

**理由**:
- 镜像体积小，便于传输
- 向量库数据可以独立备份和迁移
- 支持增量更新，无需重建镜像

**替代方案**: 构建时打包进镜像 → 镜像大，更新不方便

### 7. Docker 网络：与 go_ai_talk 共享网络

**决策**: Python 服务加入 go_ai_talk 的 Docker Compose 网络，通过服务名访问兄弟仓服务。

**理由**:
- 网络隔离，安全
- 通过服务名（history-service、device-service）访问，无需硬编码 IP
- 与 go_ai_talk 部署流程统一

**替代方案**: 独立网络 → 需要额外配置网络连通性

### 8. CI/CD：独立 GitHub Actions

**决策**: Python 项目独立仓库，使用独立的 GitHub Actions 工作流，与 go_ai_talk 的 CI/CD 对齐。

**理由**:
- 独立仓库，独立版本控制
- CI/CD 流程对齐 go_ai_talk，便于统一管理
- 支持 tag 触发自动构建推送

**替代方案**: 与 go_ai_talk 在同一仓库 → 代码混乱，构建时间长

## Risks / Trade-offs

### [风险] Python 服务延迟增加

**影响**: Python 服务增加 HTTP 调用、向量检索等步骤，可能导致延迟增加

**缓解**:
- 缓存事件字典（24h TTL）
- 并行获取历史数据和宝宝画像
- 使用异步 HTTP 客户端（httpx）
- 流式响应减少感知延迟

### [风险] LLM 调用失败

**影响**: Python 服务调用 LLM 失败时，go_ai_talk 无法正常工作

**缓解**:
- 添加重试机制
- 配置超时时间
- 返回明确的错误码
- go_ai_talk 侧添加降级处理

### [风险] 向量库数据丢失

**影响**: Chroma 向量库数据存储在 Volume 中，可能因 Volume 问题丢失

**缓解**:
- 定期备份 Volume
- 提供重建脚本
- 记录构建时间戳

### [风险] 兼容性问题

**影响**: Python 返回的 JSON 结构与 Go 期望不一致，导致 Go 侧处理失败

**缓解**:
- 严格按照 Go 的 `deepSeekUnifiedIntent` 结构体设计返回格式
- 添加测试用例验证兼容性
- 先在测试环境验证再上线

### [风险] 并发控制

**影响**: Python 服务可能超过 LLM 提供商的并发限制

**缓解**:
- Redis 闸门控制（与 Go 侧共享）
- 根据 Go 传入的 maxInFlight 控制并发
- 添加限流中间件

### [风险] 网络隔离

**影响**: Python 服务与 go_ai_talk 部署在不同网络环境时，无法访问兄弟仓服务

**缓解**:
- 使用 Docker Compose 网络（开发/测试环境）
- 使用 VPC 网络（生产环境）
- 配置网络策略允许访问内部端口

## Migration Plan

### 阶段 1: Python 服务开发

1. 创建项目骨架和依赖配置
2. 实现基础服务（LLM 客户端、HTTP 客户端、向量存储）
3. 实现意图分析接口 `/v1/analyze/intent`
4. 实现胖宝诊疗接口 `/v1/clinic/stream`
5. 实现向量库构建脚本
6. 编写 Dockerfile 和 docker-compose 配置
7. 编写 CI/CD 工作流

### 阶段 2: go_ai_talk 修改

1. 修改 `callDeepSeekUnifiedIntent` 改为调用 Python 服务
2. 修改 `callDeepSeekGrowthSuggestion` 改为调用 Python 服务
3. 修改 `callDeepSeekHistoryReply` 改为调用 Python 服务
4. 修改 `callDeepSeekDirectReply` 改为调用 Python 服务
5. 修改 `handleIntentGeneral` 改为调用 Python 服务
6. 修改 `streamClinicLLM` 改为调用 Python 服务
7. 更新 docker-compose 配置

### 阶段 3: 测试验证

1. 本地 Docker Compose 启动测试
2. 单元测试验证意图分析准确性
3. 集成测试验证端到端流程
4. 性能测试验证延迟和并发

### 阶段 4: 部署上线

1. 推送镜像到阿里云 ACR
2. 测试环境部署验证
3. 生产环境灰度发布
4. 全量上线

### 回滚策略

1. 如果 Python 服务出现问题，Go 侧可以快速切换回直接调用 LLM
2. 保留原有 LLM 调用代码，通过配置开关控制

## Open Questions

1. **Redis 闸门 key 格式**: 是否与 Go 侧使用相同的 key 格式（`llm_gate:{model}:inflight`）？需要确认 Go 侧的 key 格式。

2. **向量库重建策略**: 当知识库文档更新时，如何触发向量库重建？

3. **监控指标**: 需要监控哪些指标（延迟、成功率、并发数等）？

4. **日志格式**: 是否需要与 go_ai_talk 的日志格式对齐？

5. **配置热更新**: LLM 配置（provider/model）是否需要支持运行时热更新？
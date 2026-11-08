# Python AI Talk

本仓为 Python 微服务 monorepo：

- **python-ai-talk**（`app/`，端口 8000）：基于 FastAPI + LangGraph 的母婴喂养意图识别
- **python-prediction**（`prediction/`，端口 8001）：预测机器学习模型服务（当前为健康检查骨架）

镜像：`Dockerfile.python-ai-talk` / `Dockerfile.python-prediction`。CI 支持 `v*+talk` / `v*+prediction` 选择性推 ACR，详见 `docs/deploy-guide.md`。

## 功能特性

- **意图分析**：识别用户自然语言中的喂养记录、历史查询、成长建议等意图
- **意图缓存飞轮**：确认落库成功后缓存整句 CRUD 意图，重复表述可加速识别
- **智能陪伴**：clinic 续聊（画像/喂养史 + LLM；不通识检索；tip 已下线）
- **护理留意**：日分析内联 system 提示词 + 近期史（无 feedback / 外置 prompt 飞轮）
- **确认流程**：支持用户确认/否定反馈，结合 LangGraph MemorySaver 实现中断恢复

## 项目结构

\python_ai_talk/
├── app/                            # python-ai-talk 应用（:8000）
├── prediction/                     # python-prediction 骨架（:8001）
├── Dockerfile.python-ai-talk
├── Dockerfile.python-prediction
├── docker-compose*.yml
├── docs/deploy-guide.md
└── pyproject.toml
\
## API 接口

### 意图分析

```
POST /v1/analyze/intent
```

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `text` | string | 是 | 用户输入的自然语言文本 |
| `deviceNo` | string | 是 | 设备编号 |
| `model` | object | 是 | 模型配置（provider, name, max_in_flight） |

**响应参数**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `target_type` | string | 目标类型：feeding, history, suggest, conversation, exit |
| `action` | string | 动作类型：start, end, one, search, suggestion, reply, exit |
| `event_name` | string | 事件名称（喂养场景） |
| `keywords` | string[] | 匹配的关键词列表 |
| `content` | string | 回答内容（对话场景） |
| `match_confidence` | float | 向量匹配置信度（0-1） |
| `match_source` | string | 匹配来源：vector（向量匹配）或 llm（LLM分类） |
| `need_confirm` | bool | 是否需要用户确认 |
| `confirm_message` | string | 确认话术（need_confirm=true 时返回） |

### 意图确认反馈

```
POST /v1/analyze/intent/confirm
```

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `conversation_id` | string | 是 | 会话ID，用于恢复中断的图执行 |
| `user_feedback` | string | 是 | 用户反馈：confirm（确认）或 reject（否定） |

**响应参数**：与意图分析接口相同。

### 陪伴续聊

```
POST /v1/clinic
POST /v1/clinic/stream
```

### 护理留意 / 成长轨迹

```
POST /v1/care-alert/analyze
POST /v1/care-alert/analyze/stream
POST /v1/growth-trajectory/turn
```

### 健康检查

```
GET /health
```

## 快速开始

### 本地开发

```bash
# 安装依赖
poetry install

# 配置环境变量
cp .env.example env/.env.local

# 构建知识向量库（首次运行）
python scripts/build_vector_db.py

# 启动服务
docker compose --env-file env/.env.local \
  -f docker-compose.yml \
  -f docker-compose.local.yml \
  up -d --build
```

### 测试环境

```bash
docker compose --env-file env/.env.test \
  -f docker-compose.yml \
  -f docker-compose.test.yml \
  pull && \
docker compose --env-file env/.env.test \
  -f docker-compose.yml \
  -f docker-compose.test.yml \
  up -d --no-build
```

详细部署说明请参考 [部署指南](docs/deploy-guide.md)。

## 文档

- [部署指南](docs/deploy-guide.md) - 从零开始部署服务的完整步骤
- [向量数据库指南](docs/vector_db_guide.md) - 向量数据库构建、使用和维护说明

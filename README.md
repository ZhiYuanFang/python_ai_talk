# Python AI Talk

基于 FastAPI + LangGraph 的母婴喂养意图识别微服务。

## 功能特性

- **意图分析**：识别用户自然语言中的喂养记录、历史查询、成长建议等意图
- **胖宝诊疗**：结合向量数据库和 LLM 提供母婴健康诊疗建议
- **向量数据库**：基于 Chroma + BGE 的中文母婴知识库
- **向量匹配**：喂养事件向量库支持语义匹配，优先于 LLM 分类，降低延迟和成本
- **数据飞轮**：用户确认后自动学习表达，持续优化匹配准确率；用户否定后自动删除错误向量
- **确认流程**：支持用户确认/否定反馈，结合 LangGraph MemorySaver 实现中断恢复

## 项目结构

```
python_ai_talk/
├── app/                            # 应用代码
│   ├── main.py                     # FastAPI 入口
│   ├── api/routes/                 # API 路由
│   │   ├── intent.py               # 意图分析路由（含确认接口）
│   │   ├── clinic.py               # 诊疗问答路由
│   │   ├── health.py               # 健康检查路由
│   │   └── tip.py                  # 小贴士路由
│   ├── feeding/                    # 喂养动作相关代码
│   │   ├── graphs/                 # LangGraph 状态图
│   │   │   ├── intent_graph.py     # 意图分析图（向量匹配→分类→确认→后处理）
│   │   │   ├── nodes/              # 图节点
│   │   │   │   ├── classify_intent.py       # LLM 意图分类
│   │   │   │   ├── match_event_by_vector.py # 向量匹配
│   │   │   │   ├── prepare_confirm.py       # 准备确认
│   │   │   │   ├── handle_feedback.py       # 处理用户反馈
│   │   │   │   └── prompts/                 # LLM 提示词
│   │   │   └── states/             # 图状态定义
│   │   │       └── intent_state.py          # 意图分析状态
│   │   ├── schemas/                # 数据模型
│   │   │   └── intent.py           # 意图分析请求/响应模型
│   │   └── services/               # 业务服务
│   │       ├── event_cache.py      # 事件字典缓存（24h TTL）
│   │       └── event_vector_store.py # 喂养事件向量存储（数据飞轮）
│   ├── clinic/                     # 喂养建议相关代码
│   │   ├── graphs/                 # LangGraph 状态图
│   │   │   ├── clinic_graph.py     # 诊疗问答图
│   │   │   ├── tip_graph.py        # 小贴士图
│   │   │   ├── nodes/              # 图节点
│   │   │   └── states/             # 图状态定义
│   │   ├── schemas/                # 数据模型
│   │   └── services/               # 业务服务
│   │       └── knowledge_vector_store.py # 知识向量存储
│   ├── shared/                     # 共享服务
│   │   ├── http_client.py          # HTTP 客户端（调用兄弟仓 API）
│   │   ├── llm_client.py           # LLM 客户端（DeepSeek/GLM）
│   │   ├── redis_gate.py           # Redis 门控
│   │   └── vector_store.py         # 通用向量存储服务
│   └── config/                     # 配置管理
│       └── settings.py             # 环境变量配置
├── data/                           # 数据目录（不提交到 Git）
│   ├── chroma_db/                  # Chroma 向量库存储
│   ├── knowledge/                  # 知识库文档
│   └── models/                     # Embedding 模型缓存
├── scripts/                        # 工具脚本
│   └── build_vector_db.py          # 知识向量库构建脚本
├── docs/                           # 文档
│   ├── deploy-guide.md             # 部署指南
│   └── vector_db_guide.md          # 向量数据库指南
└── pyproject.toml                  # Python 依赖管理（Poetry）
```

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

### 胖宝诊疗

```
POST /v1/analyze/clinic
```

### 小贴士

```
POST /v1/analyze/tip
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

# Python AI Talk 部署指南

> 本文档面向新手，提供从零开始部署 Python AI Talk 服务的完整步骤。
> 部署环境为 Linux，使用 Docker 和 Docker Compose。

---

## ⚠️ 变更说明（Breaking Change）

**本次重构采用「三层一致」环境变量命名规范**：

```
旧命名（错误）              新命名（统一）
──────────────────          ──────────────────
PYTHON_AI_TALK_REDIS_URL  → REDIS_URL
PYTHON_AI_TALK_HISTORY_SERVICE_URL → HISTORY_SERVICE_URL
PYTHON_AI_TALK_DEEPSEEK_API_KEY   → DEEPSEEK_API_KEY
...其他 8 个变量同样处理
```

**变更原因**：原配置存在「三层错配」问题——`.env.*` 文件、docker-compose 注入、python 应用读取三个层级的变量名不一致，导致容器内进程实际读不到配置，只能依赖默认值 fallback。

**影响范围**：
- `env/.env.local`、`env/.env.test`、`env/.env.prod`
- `docker-compose.yml` 的 environment 段
- 兄弟仓 go_ai_talk 的 `python-ai-talk` 服务段（已同步修改）

**部署影响**：现有 `.env.*` 文件需按新格式重写；现有部署的容器需重启。

---

## 目录

- [1. 概述](#1-概述)
- [2. 目录结构说明](#2-目录结构说明)
  - [2.1 喂养事件向量库部署说明](#21-喂养事件向量库部署说明)
  - [2.2 确认流程部署说明](#22-确认流程部署说明)
  - [2.3 目录结构变更说明](#23-目录结构变更说明)
  - [2.4 意图分析流式接口说明](#24-意图分析流式接口说明)
- [3. 环境准备](#3-环境准备)
- [4. 本地开发环境部署](#4-本地开发环境部署)
- [5. 测试环境部署](#5-测试环境部署)
- [6. 生产环境部署](#6-生产环境部署)
- [7. 环境变量配置说明](#7-环境变量配置说明)
- [8. 常见问题解答](#8-常见问题解答)
- [9. 附录](#9-附录)

---

## 1. 概述

### 1.1 项目简介

Python AI Talk 是一个基于 FastAPI + LangGraph 的母婴喂养意图识别微服务，提供以下能力：

- **意图分析**：识别用户自然语言中的喂养记录、历史查询、成长建议等意图
- **胖宝诊疗**：结合向量数据库和 LLM 提供母婴健康诊疗建议
- **向量数据库**：基于 Chroma + BGE 的中文母婴知识库

### 1.2 部署架构

```
┌─────────────────────────────────────────────────────────────┐
│                    部署架构总览                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   用户请求                                                   │
│      │                                                      │
│      ▼                                                      │
│   ┌──────────────┐                                          │
│   │  go_ai_talk  │  ← 兄弟仓，提供 HTTP API、MySQL、Redis    │
│   │  (gateway)   │                                          │
│   └──────┬───────┘                                          │
│          │                                                  │
│          ▼                                                  │
│   ┌─────────────────────────────────────┐                   │
│   │        python_ai_talk               │                   │
│   │  ┌──────────┐  ┌─────────────────┐  │                   │
│   │  │ FastAPI  │  │   LangGraph     │  │                   │
│   │  │ (HTTP)   │──│ (意图识别引擎)   │  │                   │
│   │  └──────────┘  └─────────────────┘  │                   │
│   │         │                           │                   │
│   │         ▼                           │                   │
│   │  ┌──────────────┐  ┌──────────┐    │                   │
│   │  │ Chroma 向量库 │  │ DeepSeek │    │                   │
│   │  │ (本地存储)    │  │  LLM API │    │                   │
│   │  └──────────────┘  └──────────┘    │                   │
│   └─────────────────────────────────────┘                   │
│                                                             │
│   python_ai_talk 依赖 go_ai_talk 的：                        │
│   • history-service (端口 9801)                              │
│   • device-service  (端口 9803)                              │
│   • voice-service   (端口 9802)                              │
│   • Redis                                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 多环境说明

本项目支持三套环境，通过 Docker Compose overlay 模式管理：

| 环境 | 用途 | 项目名 | 端口 | 镜像来源 |
|------|------|--------|------|----------|
| **local** | 本地开发 | python-ai-talk-local | 8000 | 本地构建 |
| **test** | 测试验证 | python-ai-talk-test | 18000 | ACR 测试仓库 |
| **prod** | 生产运行 | python-ai-talk-prod | 8000 | ACR 生产仓库 |

---

## 2. 目录结构说明

```
python_ai_talk/
├── docker-compose.yml              # 基线配置（定义服务骨架，所有环境共用）
├── docker-compose.local.yml        # 本地开发 overlay（端口、网络、extra_hosts）
├── docker-compose.test.yml         # 测试环境 overlay（镜像、端口、网络）
├── docker-compose.prod.yml         # 生产环境 overlay（镜像、端口、网络）
├── Dockerfile                      # Docker 镜像构建文件
├── .env.example                    # 环境变量模板（提交到 Git，不含真实密钥）
├── .gitignore                      # Git 忽略规则
│
├── env/                            # 环境变量文件目录（不提交到 Git）
│   ├── .env.local                  # 本地开发环境变量
│   ├── .env.test                   # 测试环境变量
│   └── .env.prod                   # 生产环境变量
│
├── docs/                           # 文档目录
│   └── deploy-guide.md             # 本文件
│
├── app/                            # 应用代码
│   ├── main.py                     # FastAPI 入口
│   ├── api/                        # API 路由
│   │   └── routes/                 # 路由模块
│   │       ├── intent.py           # 意图分析路由（含确认接口）
│   │       ├── clinic.py           # 诊疗问答路由
│   │       ├── health.py           # 健康检查路由
│   │       └── tip.py              # 小贴士路由
│   ├── feeding/                    # 喂养动作相关代码
│   │   ├── graphs/                 # LangGraph 状态图和节点
│   │   ├── schemas/                # 数据模型
│   │   └── services/               # 事件缓存、事件向量存储
│   ├── clinic/                     # 喂养建议相关代码
│   │   ├── graphs/                 # LangGraph 状态图和节点
│   │   ├── schemas/                # 数据模型
│   │   └── services/               # 知识向量存储
│   ├── shared/                     # 共享服务
│   │   ├── http_client.py          # HTTP 客户端
│   │   ├── llm_client.py           # LLM 客户端
│   │   ├── redis_gate.py           # Redis 门控
│   │   └── vector_store.py         # 通用向量存储
│   └── config/                     # 配置管理
│
├── scripts/                        # 工具脚本
│   └── build_vector_db.py          # 向量数据库构建脚本
│
├── data/                           # 数据目录（不提交到 Git）
│   ├── chroma_db/                  # Chroma 向量库存储
│   └── models/                     # Embedding 模型缓存
│
└── pyproject.toml                  # Python 依赖管理（Poetry）
```

### 文件关系说明

```
基线 (docker-compose.yml)
  ├── 定义服务骨架：python-ai-talk
  ├── 定义 healthcheck、volumes
  └── 定义 environment（引用 ${VAR} 占位符）
       │
       ├─ 本地 overlay (docker-compose.local.yml)
       │    ├── 添加 ports: 8000:8000
       │    ├── 添加 extra_hosts
       │    └── 添加 networks: go-ai-talk-net
       │
       ├─ 测试 overlay (docker-compose.test.yml)
       │    ├── 添加 image: ${REGISTRY}/python-ai-talk:${IMAGE_TAG}
       │    ├── 添加 ports: 18000:8000
       │    └── 添加 networks: python-ai-talk-test-net
       │
       └─ 生产 overlay (docker-compose.prod.yml)
            ├── 添加 image: ${REGISTRY}/python-ai-talk:${IMAGE_TAG}
            ├── 添加 ports: 8000:8000
            └── 添加 networks: go-ai-talk-net

环境变量 (.env.*)
  └── 完整定义所有 ${VAR} 的实际值
```

---

## 2.1 喂养事件向量库部署说明

### 2.1.1 概述

喂养事件向量库使用独立的 ChromaDB Collection（`feeding_events`）存储事件向量，与母婴知识向量库（`mother_baby_knowledge`）物理隔离。

### 2.1.2 自动创建机制

- `feeding_events` Collection 在服务启动时自动创建，无需手动执行构建脚本
- 服务启动时 `EventVectorStore` 初始化会调用 `get_or_create_collection`，如果 Collection 不存在则自动创建
- 向量库的 Embedding 模型与知识向量库相同（`BAAI/bge-small-zh-v1.5`），共享模型缓存

### 2.1.3 事件字典依赖

- 喂养事件向量库依赖事件字典 API（通过 HTTP 从 `history-service` 获取）
- 事件字典由 `EventCache` 管理，TTL 为 24 小时
- **首次启动需要等待事件字典获取完成后才能使用向量匹配**，否则向量库中没有标准事件数据
- 首次获取事件字典时会自动初始化向量库（`initialize_events`），为所有事件生成标准条目和动作变体

### 2.1.4 ChromaDB Volume 挂载路径

| 环境 | 容器内路径 | 宿主机挂载 |
|------|-----------|-----------|
| 本地开发 | `/app/data/chroma_db` | 项目 `data/chroma_db/` 目录 |
| 测试环境 | `/app/data/chroma_db` | Docker Volume |
| 生产环境 | `/app/data/chroma_db` | Docker Volume |

> **注意**：`feeding_events` 和 `mother_baby_knowledge` 共用同一个 ChromaDB 持久化目录（`CHROMA_PERSIST_DIR`），通过 Collection 名称隔离。数据备份和恢复时需同时包含两个 Collection。

---

## 2.2 确认流程部署说明

### 2.2.1 新增接口

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 意图分析 | POST | `/v1/analyze/intent` | 原有接口，新增 `need_confirm` 和 `confirm_message` 响应字段 |
| 意图分析（流式） | POST | `/v1/analyze/intent/stream` | **新增**，SSE 流式返回思考进度和最终结果 |
| 意图确认反馈 | POST | `/v1/analyze/intent/confirm` | **新增**，接收用户确认/否定反馈 |

### 2.2.2 确认流程说明

当意图分析结果需要用户确认时，流程如下：

1. 用户发送消息，调用 `/v1/analyze/intent`
2. 服务返回 `need_confirm=true` 和 `confirm_message`（如"您是想记录喂奶吗？"）
3. 客户端展示确认话术，用户点击确认或否定
4. 客户端调用 `/v1/analyze/intent/confirm`，传入 `conversation_id` 和 `user_feedback`（`confirm` 或 `reject`）
5. 服务恢复中断的图执行，返回最终意图结果

### 2.2.3 go_ai_talk 配合要求

- 需要go_ai_talk配合实现用户确认UI，包括：
  - 展示确认话术（`confirm_message` 字段）
  - 提供确认/否定按钮
  - 调用确认接口时传入 `conversation_id`（从意图分析响应中获取）
  - 传入 `user_feedback` 为 `"confirm"` 或 `"reject"`

### 2.2.4 状态管理

- 确认流程使用 **LangGraph MemorySaver** 进行状态管理
- MemorySaver 是内存级检查点，服务重启后中断的确认会话会丢失
- `conversation_id` 作为 LangGraph 的 `thread_id`，用于恢复检查点
- 如需持久化检查点，可替换为数据库存储的 Checkpointer（如 PostgreSQL）

---

## 2.3 目录结构变更说明

近期项目结构进行了模块化重构，新增了以下目录：

```
app/
├── feeding/                    # 喂养动作相关代码
│   ├── graphs/                 # LangGraph 状态图
│   │   ├── intent_graph.py     # 意图分析图（含向量匹配、确认流程）
│   │   ├── nodes/              # 图节点
│   │   │   ├── classify_intent.py       # LLM 意图分类
│   │   │   ├── match_event_by_vector.py # 向量匹配
│   │   │   ├── prepare_confirm.py       # 准备确认
│   │   │   ├── handle_feedback.py       # 处理用户反馈
│   │   │   └── prompts/                 # LLM 提示词
│   │   └── states/            # 图状态定义
│   │       └── intent_state.py          # 意图分析状态
│   ├── schemas/                # 数据模型
│   │   └── intent.py           # 意图分析请求/响应模型
│   └── services/               # 业务服务
│       ├── event_cache.py      # 事件字典缓存（24h TTL）
│       └── event_vector_store.py # 喂养事件向量存储
│
├── clinic/                     # 喂养建议相关代码
│   ├── graphs/                 # LangGraph 状态图
│   │   ├── clinic_graph.py     # 诊疗问答图
│   │   ├── tip_graph.py        # 小贴士图
│   │   ├── nodes/              # 图节点
│   │   └── states/             # 图状态定义
│   ├── schemas/                # 数据模型
│   └── services/               # 业务服务
│       └── knowledge_vector_store.py # 知识向量存储
│
└── shared/                     # 共享服务
    ├── http_client.py          # HTTP 客户端（调用兄弟仓 API）
    ├── llm_client.py           # LLM 客户端（DeepSeek/GLM）
    ├── redis_gate.py           # Redis 门控
    └── vector_store.py         # 通用向量存储服务
```

**与旧目录的对应关系**：

| 旧目录 | 新目录 | 说明 |
|--------|--------|------|
| `app/services/` | `app/shared/` | 共享服务迁入 shared |
| `app/graphs/intent_graph.py` | `app/feeding/graphs/intent_graph.py` | 意图图迁入 feeding |
| `app/graphs/states/intent_state.py` | `app/feeding/graphs/states/intent_state.py` | 意图状态迁入 feeding |
| `app/services/event_cache.py` | `app/feeding/services/event_cache.py` | 事件缓存迁入 feeding |
| - | `app/feeding/services/event_vector_store.py` | 新增：事件向量存储 |
| - | `app/clinic/services/knowledge_vector_store.py` | 知识向量从 services 迁入 clinic |

---

## 2.4 意图分析流式接口说明

### 2.4.1 概述

意图分析流式接口 `/v1/analyze/intent/stream` 通过 SSE（Server-Sent Events）协议返回意图分析过程和结果，让前端实时感知 LangGraph 节点的思考进度，提升用户交互体验。

该接口与 `/v1/analyze/intent`（非流式）功能等价，区别仅在于响应格式：
- **非流式**：等待全部节点执行完毕后一次性返回 JSON 响应
- **流式**：每个节点完成时推送 `thinking` 事件，最后推送 `answer` 事件

### 2.4.2 请求参数

请求体与 `/v1/analyze/intent` 完全一致（`stream` 字段在流式端点中被忽略，始终以流式方式返回）：

```json
{
  "text": "开始母乳",
  "deviceNo": "DEVICE_001",
  "model": {
    "provider": "deepseek",
    "name": "deepseek-chat",
    "max_in_flight": 3
  },
  "stream": true
}
```

### 2.4.3 SSE 响应格式

响应 Content-Type 为 `text/event-stream`，包含三类事件：

#### 1. thinking 事件（节点思考进度）

每个 LangGraph 节点完成时推送一条 `thinking` 事件：

```
data: {"type": "thinking", "content": "正在匹配喂养事件...", "node": "match_event_by_vector"}

```

| 字段 | 说明 |
|------|------|
| `type` | 固定为 `"thinking"` |
| `content` | 节点对应的中文思考文案 |
| `node` | 节点名称（如 `match_event_by_vector`、`classify_intent` 等） |

**节点思考文案映射**：

| 节点名 | 思考文案 |
|--------|----------|
| `match_event_by_vector` | 正在匹配喂养事件... |
| `classify_intent` | 正在分析意图... |
| `prepare_confirm` | 正在生成确认话术... |
| `handle_feedback` | 正在处理用户反馈... |
| `call_clinic_agent` | 正在获取喂养建议... |
| `judge_data_requirement` | 正在判断数据需求... |
| `fetch_history` | 正在拉取历史记录... |
| `search_vectors` | 正在检索相关知识... |
| `fetch_baby_profile` | 正在获取宝宝画像... |
| `generate_response` | 正在生成回答... |

#### 2. answer 事件（最终意图结果）

全部节点完成后推送一条 `answer` 事件，包含完整意图分析结果：

```
data: {"type": "answer", "content": "{\"target_type\":\"feeding\",\"action\":\"start\",\"event_name\":\"母乳\",\"need_confirm\":true,\"confirm_message\":\"您是要开始记录「母乳」吗？...\"}"}

```

`content` 字段为 IntentResponse 的 JSON 字符串，字段说明：

| 字段 | 类型 | 说明 |
|------|------|------|
| `target_type` | string | 目标类型：feeding, history, suggest, conversation, exit |
| `action` | string | 动作类型：start, end, one, search, suggestion, reply, exit |
| `event_name` | string | 事件名称（喂养场景） |
| `keywords` | string[] | 匹配的关键词列表 |
| `content` | string | 回答内容（对话场景） |
| `need_confirm` | boolean | 是否需要用户确认 |
| `confirm_message` | string | 确认话术（need_confirm=true 时返回） |
| `conversation_id` | string | 会话ID（用于调用 confirm 接口） |

#### 3. [DONE] 结束标记

流式传输结束时推送：

```
data: [DONE]

```

### 2.4.4 完整响应示例

```
data: {"type": "thinking", "content": "正在匹配喂养事件...", "node": "match_event_by_vector"}

data: {"type": "thinking", "content": "正在生成确认话术...", "node": "prepare_confirm"}

data: {"type": "answer", "content": "{\"target_type\":\"feeding\",\"action\":\"start\",\"event_name\":\"母乳\",\"keywords\":[\"母乳\"],\"need_confirm\":true,\"confirm_message\":\"您是要开始记录「母乳」吗？请回复「确认」或「取消」。\"}"}

data: [DONE]

```

### 2.4.5 conversation/suggest 意图内部调用 clinic agent

当意图被识别为 `conversation`（对话）或 `suggest`（建议）时，意图图内部的 `call_clinic_agent` 节点会直接调用 `clinic_graph` 获取回答，前端无需发起第二次 HTTP 请求：

- `clinic_graph` 完成数据准备（判断数据需求→拉取历史→向量检索→获取宝宝画像）
- 复用 `generate_response` 节点调用 LLM 生成回答
- 失败时返回兜底文案"抱歉，我暂时无法回答您的问题，请稍后再试。"
- 最终以 `conversation` 类型、`reply` 动作返回

### 2.4.6 前端接入注意事项

1. **SSE 客户端**：前端需使用 SSE 客户端（如 EventSource 或 fetch + ReadableStream）接收流式响应
2. **事件解析**：每条事件以 `data: ` 开头，以 `\n\n` 分隔，需解析 JSON 内容
3. **结束判断**：收到 `data: [DONE]` 表示流结束，应关闭连接
4. **thinking 展示**：thinking 事件可实时展示在 UI 上，让用户感知 AI 思考过程
5. **answer 处理**：answer 事件的 content 字段需 JSON.parse 后使用，包含完整意图结果
6. **确认流程**：若 answer 中 `need_confirm=true`，应展示确认话术并调用 `/v1/analyze/intent/confirm` 接口
7. **超时处理**：流式请求可能耗时较长（LLM 调用），前端应设置合理的超时时间（建议 60 秒）

---

## 3. 环境准备

### 3.1 安装 Docker

**步骤 1：检查是否已安装**

```bash
docker --version
docker compose version
```

如果显示版本号，说明已安装，跳到 3.2。

**步骤 2：安装 Docker（如未安装）**

```bash
# 更新包索引
sudo apt-get update

# 安装依赖
sudo apt-get install -y ca-certificates curl gnupg

# 添加 Docker 官方 GPG 密钥
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# 添加 Docker 软件源
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker

# 将当前用户加入 docker 组（免 sudo 使用 docker）
sudo usermod -aG docker $USER
newgrp docker
```

**步骤 3：验证安装**

```bash
docker --version
# 预期输出类似：Docker version 24.0.0, build 1234567

docker compose version
# 预期输出类似：Docker Compose version v2.20.0
```

### 3.2 创建 Docker 网络

Python AI Talk 需要与 go_ai_talk 的服务在同一个 Docker 网络中通信。

```bash
# 创建本地开发网络
docker network create go-ai-talk-net

# 创建测试环境网络
docker network create go-ai-talk-test-net
```

> **注意**：生产环境使用 `go-ai-talk-net`，由 go_ai_talk 的生产部署创建。

### 3.3 登录阿里云容器镜像服务（ACR）

**仅测试/生产环境需要，本地开发不需要。**

```bash
# 使用阿里云账号密码登录
docker login --username=<你的阿里云账号> \
  crpi-lff3xynwzvqxxxjk-vpc.cn-hangzhou.personal.cr.aliyuncs.com

# 输入密码（来自 env/.env.test 或 env/.env.prod 中的 ACR_PASSWORD）
```

> **获取登录信息**：
> - 测试环境仓库：`crpi-lff3xynwzvqxxxjk-vpc.cn-hangzhou.personal.cr.aliyuncs.com/pangbao-test`
> - 生产环境仓库：`crpi-lff3xynwzvqxxxjk-vpc.cn-hangzhou.personal.cr.aliyuncs.com/pangbao-release`

### 3.4 克隆代码仓库

```bash
# 克隆项目
git clone <你的仓库地址> python_ai_talk
cd python_ai_talk
```

---

## 4. 本地开发环境部署

### 4.1 前置条件

- Docker 和 Docker Compose 已安装
- Docker 网络 `go-ai-talk-net` 已创建
- go_ai_talk 的本地服务已启动（history-service、device-service、voice-service）
- 或者通过 `host.docker.internal` 访问宿主机上的服务

### 4.2 配置环境变量

```bash
# 复制环境变量模板
cp .env.example env/.env.local

# 编辑环境变量文件
nano env/.env.local
```

**必须修改的变量**：

| 变量名 | 说明 | 示例值 |
|--------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | `sk-xxx...` |
| `GLM_API_KEY` | 智谱 GLM API 密钥 | `xxx...` |

> **获取 API Key**：
> - DeepSeek：https://platform.deepseek.com/
> - 智谱 GLM：https://open.bigmodel.cn/

### 4.3 构建向量数据库（首次运行）

```bash
# 创建数据目录
mkdir -p data/chroma_db data/models

# 构建向量数据库（需要先安装 Python 依赖）
poetry install
poetry shell
python scripts/build_vector_db.py
```

> **注意**：如果已有构建好的向量数据库，可以直接复制到 `data/chroma_db/` 目录。

### 4.4 启动服务

```bash
# 启动本地开发环境（--build 表示构建镜像）
docker compose --env-file env/.env.local \
  -f docker-compose.yml \
  -f docker-compose.local.yml \
  up -d --build
```

**命令说明**：
- `--env-file env/.env.local`：指定环境变量文件
- `-f docker-compose.yml`：基线配置
- `-f docker-compose.local.yml`：本地开发 overlay
- `up -d`：后台启动
- `--build`：构建镜像（修改代码后需要重新构建）

### 4.5 验证服务状态

```bash
# 查看容器状态
docker compose --env-file env/.env.local \
  -f docker-compose.yml \
  -f docker-compose.local.yml \
  ps

# 预期输出：python-ai-talk 状态为 healthy

# 查看服务日志
docker compose --env-file env/.env.local \
  -f docker-compose.yml \
  -f docker-compose.local.yml \
  logs -f python-ai-talk

# 测试健康检查接口
curl http://localhost:8000/health
# 预期输出：{"status":"ok"}
```

### 4.6 停止服务

```bash
docker compose --env-file env/.env.local \
  -f docker-compose.yml \
  -f docker-compose.local.yml \
  down
```

---

## 5. 测试环境部署

### 5.1 前置条件

- Docker 和 Docker Compose 已安装
- Docker 网络 `go-ai-talk-test-net` 已创建
- 已登录 ACR 镜像仓库
- go_ai_talk 的测试环境已启动

### 5.2 配置环境变量

```bash
# 环境变量文件已由团队配置好，通常不需要修改
# 如需修改，联系运维人员获取最新的 env/.env.test
```

### 5.3 启动服务

```bash
# 拉取镜像并启动测试环境
docker compose --env-file env/.env.test \
  -f docker-compose.yml \
  -f docker-compose.test.yml \
  pull && \
docker compose --env-file env/.env.test \
  -f docker-compose.yml \
  -f docker-compose.test.yml \
  up -d --no-build
```

**命令说明**：
- `pull`：从 ACR 拉取最新镜像
- `up -d --no-build`：后台启动，不构建镜像（测试/生产使用预构建镜像）

### 5.4 验证服务状态

```bash
# 查看容器状态
docker compose --env-file env/.env.test \
  -f docker-compose.yml \
  -f docker-compose.test.yml \
  ps

# 测试健康检查接口（注意端口是 18000）
curl http://localhost:18000/health
# 预期输出：{"status":"ok"}
```

### 5.5 停止服务

```bash
docker compose --env-file env/.env.test \
  -f docker-compose.yml \
  -f docker-compose.test.yml \
  down
```

---

## 6. 生产环境部署

### 6.1 前置条件

- Docker 和 Docker Compose 已安装
- Docker 网络 `go-ai-talk-net` 已存在（由 go_ai_talk 生产部署创建）
- 已登录 ACR 镜像仓库
- go_ai_talk 的生产环境已启动

### 6.2 配置环境变量

```bash
# 环境变量文件 env/.env.prod 已由运维人员配置
# 确保文件存在且密钥正确
ls env/.env.prod
```

> **安全提醒**：生产环境密钥必须与测试环境不同，且不得泄露！

### 6.3 启动服务

```bash
# 拉取镜像并启动生产环境
docker compose --env-file env/.env.prod \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  pull && \
docker compose --env-file env/.env.prod \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  up -d --no-build
```

### 6.4 验证服务状态

```bash
# 查看容器状态
docker compose --env-file env/.env.prod \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  ps

# 测试健康检查接口
curl http://localhost:8000/health
# 预期输出：{"status":"ok"}
```

### 6.5 回滚操作

如果新版本出现问题，可以快速回滚到上一个版本：

```bash
# 步骤 1：停止当前服务
docker compose --env-file env/.env.prod \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  down

# 步骤 2：修改 env/.env.prod 中的 IMAGE_TAG 为上一个版本
# 例如：IMAGE_TAG=v2.0.23
nano env/.env.prod

# 步骤 3：重新拉取旧版本镜像并启动
docker compose --env-file env/.env.prod \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  pull && \
docker compose --env-file env/.env.prod \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  up -d --no-build
```

### 6.6 停止服务

```bash
docker compose --env-file env/.env.prod \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  down
```

---

## 7. 环境变量配置说明

### 7.1 完整变量清单

| 变量名 | 用途 | 必填 | 本地示例 | 测试示例 | 生产示例 |
|--------|------|------|----------|----------|----------|
| `REGISTRY` | ACR 仓库地址 | 测试/生产 | - | `...pangbao-test` | `...pangbao-release` |
| `IMAGE_TAG` | 镜像版本号 | 测试/生产 | - | `v2.0.7-beta.43` | `v2.0.24` |
| `ACR_USERNAME` | ACR 登录账号 | 测试/生产 | - | `8区投投` | `8区投投` |
| `ACR_PASSWORD` | ACR 登录密码 | 测试/生产 | - | `Fang930927` | `Fang930927` |
| `REDIS_URL` | Redis 连接地址 | 是 | `redis://localhost:6379/0` | `redis://redis-test:6379/0` | `redis://redis-node-1:7001,...` |
| `HISTORY_SERVICE_URL` | history-service 地址 | 是 | `http://host.docker.internal:9801` | `http://history-service:9801` | `http://history-service:9801` |
| `DEVICE_SERVICE_URL` | device-service 地址 | 是 | `http://host.docker.internal:9803` | `http://device-service:9803` | `http://device-service:9803` |
| `VOICE_SERVICE_URL` | voice-service 地址 | 是 | `http://host.docker.internal:9802` | `http://voice-service:9802` | `http://voice-service:9802` |
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | 是 | `sk-xxx` | `sk-xxx` | `sk-xxx` |
| `GLM_API_KEY` | 智谱 GLM API 密钥 | 是 | `xxx` | `xxx` | `xxx` |
| `CHROMA_PERSIST_DIR` | 向量库存储路径 | 否 | `/app/data/chroma_db` | `/app/data/chroma_db` | `/app/data/chroma_db` |
| `EMBEDDING_MODEL` | Embedding 模型 | 否 | `BAAI/bge-small-zh-v1.5` | `BAAI/bge-small-zh-v1.5` | `BAAI/bge-small-zh-v1.5` |

### 7.2 变量获取途径

| 变量 | 获取方式 |
|------|----------|
| `REGISTRY` / `IMAGE_TAG` / `ACR_USERNAME` / `ACR_PASSWORD` | 由运维人员提供，或查看 ACR 控制台 |
| `DEEPSEEK_API_KEY` | [DeepSeek 开放平台](https://platform.deepseek.com/) 创建 API Key |
| `GLM_API_KEY` | [智谱 AI 开放平台](https://open.bigmodel.cn/) 创建 API Key |
| `REDIS_URL` | 与 go_ai_talk 的 Redis 配置对齐 |
| 服务地址 | 与 go_ai_talk 的服务发现配置对齐 |

---

## 8. 常见问题解答

### Q1: 服务启动失败，如何排查？

**排查步骤**：

```bash
# 1. 查看容器日志
docker compose --env-file env/.env.local \
  -f docker-compose.yml \
  -f docker-compose.local.yml \
  logs -f python-ai-talk

# 2. 查看容器状态
docker compose --env-file env/.env.local \
  -f docker-compose.yml \
  -f docker-compose.local.yml \
  ps

# 3. 检查 Docker 网络连通性
docker network inspect go-ai-talk-net

# 4. 检查环境变量是否正确注入
docker compose --env-file env/.env.local \
  -f docker-compose.yml \
  -f docker-compose.local.yml \
  config
```

**常见原因**：
- 环境变量未正确配置（尤其是 API Key）
- Docker 网络未创建
- 依赖服务（go_ai_talk）未启动
- 端口被占用

### Q2: 镜像拉取失败，如何排查？

**排查步骤**：

```bash
# 1. 检查 ACR 登录状态
docker login crpi-lff3xynwzvqxxxjk-vpc.cn-hangzhou.personal.cr.aliyuncs.com

# 2. 检查网络连通性（VPC 环境内）
ping crpi-lff3xynwzvqxxxjk-vpc.cn-hangzhou.personal.cr.aliyuncs.com

# 3. 检查镜像版本是否存在
docker pull crpi-lff3xynwzvqxxxjk-vpc.cn-hangzhou.personal.cr.aliyuncs.com/pangbao-test/python-ai-talk:v2.0.7-beta.43
```

**常见原因**：
- ACR 登录过期（Token 有效期 12 小时）
- 镜像版本号错误
- 网络不通（检查是否在内网/VPC 环境）

### Q3: 健康检查持续失败，如何排查？

**排查步骤**：

```bash
# 1. 进入容器内部检查
 docker exec -it go-ai-talk-python-ai-talk sh

# 2. 在容器内测试健康检查接口
wget -q -O - http://127.0.0.1:8000/health

# 3. 检查向量数据库是否已构建
ls -la /app/data/chroma_db/

# 4. 检查依赖服务是否可达
wget -q -O - http://history-service:9801/api.json
```

**常见原因**：
- 向量数据库未构建（首次运行需要构建）
- 依赖服务（history-service、device-service、voice-service）不可用
- API Key 无效导致 LLM 初始化失败
- 端口未正确监听

### Q4: 如何查看服务日志？

```bash
# 实时查看日志
docker compose --env-file env/.env.local \
  -f docker-compose.yml \
  -f docker-compose.local.yml \
  logs -f python-ai-talk

# 查看最近 100 行日志
docker compose --env-file env/.env.local \
  -f docker-compose.yml \
  -f docker-compose.local.yml \
  logs --tail=100 python-ai-talk
```

### Q5: 如何重启服务？

```bash
# 方式 1：重启容器（不重建）
docker compose --env-file env/.env.local \
  -f docker-compose.yml \
  -f docker-compose.local.yml \
  restart python-ai-talk

# 方式 2：停止后重新启动
docker compose --env-file env/.env.local \
  -f docker-compose.yml \
  -f docker-compose.local.yml \
  down && \
docker compose --env-file env/.env.local \
  -f docker-compose.yml \
  -f docker-compose.local.yml \
  up -d --build
```

### Q6: 本地开发时如何修改代码后生效？

修改代码后需要重新构建镜像：

```bash
docker compose --env-file env/.env.local \
  -f docker-compose.yml \
  -f docker-compose.local.yml \
  up -d --build
```

或者使用 volume 挂载实现热更新（需要修改 docker-compose.local.yml 添加 volume 映射）。

---

## 9. 附录

### 9.1 常用命令速查

| 操作 | 命令 |
|------|------|
| 本地启动 | `docker compose --env-file env/.env.local -f docker-compose.yml -f docker-compose.local.yml up -d --build` |
| 本地停止 | `docker compose --env-file env/.env.local -f docker-compose.yml -f docker-compose.local.yml down` |
| 测试启动 | `docker compose --env-file env/.env.test -f docker-compose.yml -f docker-compose.test.yml pull && up -d --no-build` |
| 生产启动 | `docker compose --env-file env/.env.prod -f docker-compose.yml -f docker-compose.prod.yml pull && up -d --no-build` |
| 查看日志 | `docker compose --env-file env/.env.xxx -f docker-compose.yml -f docker-compose.xxx.yml logs -f python-ai-talk` |
| 查看状态 | `docker compose --env-file env/.env.xxx -f docker-compose.yml -f docker-compose.xxx.yml ps` |
| 进入容器 | `docker exec -it go-ai-talk-python-ai-talk sh` |
| 查看配置 | `docker compose --env-file env/.env.xxx -f docker-compose.yml -f docker-compose.xxx.yml config` |

### 9.2 参考链接

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 官方文档](https://docs.docker.com/compose/)
- [DeepSeek API 文档](https://platform.deepseek.com/)
- [智谱 AI 开放平台](https://open.bigmodel.cn/)
- [go_ai_talk 项目](https://github.com/your-org/go_ai_talk) （兄弟仓）

### 9.3 联系运维

遇到问题请联系运维团队：
- 测试环境部署问题
- ACR 镜像仓库问题
- 生产环境密钥管理

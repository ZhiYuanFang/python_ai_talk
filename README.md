# Python AI Talk

飞轮 / Gateway HTTP tools / 知识库。**智能体编排在 OpenClaw Gateway**，不是本进程。

## 和以前差在哪（部署）

| 以前（LangGraph） | 现在（OpenClaw） |
|-------------------|------------------|
| 只起本仓 Python = 智能体 | 先起 **Gateway**，再起本仓（tools） |
| Go → `PYTHON_AI_TALK_URL` `/v1/analyze\|clinic\|…` | Go → `OPENCLAW_GATEWAY_URL` `/v1/chat/completions` |
| prompt 在 `app/**/prompts` + 图 | `deploy/openclaw/workspaces/{intent,clinic,care_alert}/` |
| 写史在 Python 图里 | Gateway tools → Go REST / 本仓 `/v1/tools` |

云上通常要跑：**Gateway + 本仓 Python + Go**（Go 可另机）。

## 最短部署

### 1. Gateway（智能体）

```bash
# Node 需 >=22.22.3 或 >=24.15
node -v
npm install -g openclaw@2026.7.1-2

# 把本仓 deploy/openclaw 拷到服务器，进入该目录
cd deploy/openclaw
# 编辑 openclaw.json5：改 token；historyBaseUrl / toolsBaseUrl 指向 Go 与本仓
export OPENCLAW_GATEWAY_TOKEN='你的token'
# 插件（可选，装 history/飞轮 tools）
cd plugins/pangbao-tools && npm install && npm run build && cd ../..

openclaw gateway run --port 18789 --force
# 或：docker compose -f docker-compose.openclaw.yml up -d
```

验收：

```bash
curl -sS http://127.0.0.1:18789/v1/models \
  -H "Authorization: Bearer $OPENCLAW_GATEWAY_TOKEN"
```

### 2. 本仓 Python（tools，不是编排入口）

```bash
cp .env.example env/.env.local   # 按需改 REDIS / HISTORY / LLM
docker compose --env-file env/.env.local \
  -f docker-compose.yml -f docker-compose.local.yml \
  up -d --build
```

验收：

```bash
curl -sS http://127.0.0.1:8000/v1/health
# 现行面：/v1/tools/* 、/v1/knowledge/* ；不要再调 /v1/analyze/*
```

### 3. Go（业务壳）

配置：

```bash
export OPENCLAW_GATEWAY_URL=http://<gateway主机>:18789
export OPENCLAW_GATEWAY_TOKEN='与 Gateway 相同'
# PYTHON_AI_TALK_URL 若仍存在：仅非编排遗留，Intent/Clinic/Care 不要走它
```

Go 请求头需带 `x-openclaw-model`、`x-openclaw-session-key`（如 `intent:{deviceNo}`）。

## 本仓目录（查阅）

```
app/api/routes/     # health + openclaw_tools + knowledge
app/shared/         # 飞轮门面、LLM、HTTP、向量
deploy/openclaw/    # Gateway 配置、workspaces、plugins
```

## 文档

- 部署以**本文**为准。旧版长文见 [docs/deploy-guide.md](docs/deploy-guide.md)（文首已声明过期）。
- 向量库细节：[docs/vector_db_guide.md](docs/vector_db_guide.md)

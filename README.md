# Python AI Talk

飞轮 / 塑形 History tools / 知识库 / **智能体门禁与控制台**。编排在 OpenClaw Gateway；对外请走本服务门禁。

## 架构（摘要）

| 角色 | 说明 |
|------|------|
| 门禁 `POST /agent-gate/v1/chat/completions` | 校验 **G Token** → 转发内部 Gateway；**不**转发 `x-openclaw-model` |
| 控制台 `/console` | 签发 G↔A（1:1）、配置各 tool **完整 URL** |
| Tools `/v1/tools/*` | 按 **A Token** 路由上游并塑形；无默认 Go 域名 |
| Gateway 插件 | 仅 `toolsBaseUrl`，转发 `x-pangbao-api-token` |

编排 LLM 当前写死为 **`deepseek/deepseek-v4-flash`**（`openclaw.json5` → `agents.defaults.model`，并在 `models.providers.deepseek` **显式登记**）。  
Go 仍可发送 `x-openclaw-model`，但门禁会丢弃，**暂不生效**。请求 body 的 `model`（`openclaw/intent|clinic|care_alert`）仍用于选择 agent。

建议启动顺序：**建网 → OpenClaw Gateway → 本仓 Python → 打开控制台手配 → Go 指门禁**。

Python 与 OpenClaw 共 Docker 网络 **`ai_agent_net`**（本仓自管，不再用 `go-ai-talk-net`）。并网 URL：

- Python → Gateway：`INTERNAL_GATEWAY_URL=http://openclaw-gateway:18789`
- Gateway → Python：`toolsBaseUrl=http://python-ai-talk:8000/v1`

Go 经宿主机/内网访问门禁即可，不必加入 `ai_agent_net`。**勿对公网裸放 Gateway `:18789`**。

---

## 0. 建网（一次性）

```bash
docker network create ai_agent_net
# 测试栈另建：docker network create ai_agent_test_net
```

---

## 1. 启动智能体（OpenClaw Gateway）

要求：Node `>=22.22.3` 或 `>=24.15`（已含在预装镜像基线）；钉死发行版 `openclaw@2026.7.1-2`（写在 `deploy/openclaw/Dockerfile`）。

密钥在 **`deploy/openclaw/env/`**（与根目录 `env/` 分离；真值 gitignore，只提交 `.env.example`）：

- `OPENCLAW_GATEWAY_TOKEN`：进门令牌，须与 Python `INTERNAL_GATEWAY_TOKEN` 一致
- `DEEPSEEK_API_KEY`：Gateway 调 DeepSeek（当前写死 `deepseek-v4-flash`；Go 注模头被门禁忽略）

根目录 `env/.env.*` 里的 LLM key **仍留给 Python 飞轮 / tools**，不要删；改 key 时请同步 OpenClaw 这份 env。

改 `openclaw.json5`（含默认 model / `models.providers`）后：对该 compose **up -d --force-recreate**（或 restart）即可，不必 rebuild 镜像。若容器内曾生成空的 `~/.openclaw/agents/*/agent/models.json`（`"providers": {}`），recreate 前可删掉，避免盖住显式登记。

```bash
cd deploy/openclaw

# 首次：复制模板并填密钥（可从仓库根 env/.env.prod 对齐 LLM key 与 INTERNAL_GATEWAY_TOKEN）
cp env/.env.example env/.env.prod
# 编辑 env/.env.prod …

# openclaw.json5：gateway.mode=local；auth.token 引用 OPENCLAW_GATEWAY_TOKEN；
# agents 用 list；并网 toolsBaseUrl=http://python-ai-talk:8000/v1

# 本仓插件（改插件源码后才需要再跑）
cd plugins/pangbao-tools && npm install && npm run build && cd ../..

# 1) 构建预装 openclaw 的镜像（首次或升版 / 改 Dockerfile 时）
docker compose --env-file env/.env.prod \
  -f docker-compose.openclaw.yml build

# 2) 启动（必须 --env-file，否则容器无 LLM key / token）
docker compose --env-file env/.env.prod \
  -f docker-compose.openclaw.yml up -d
# 测试环境：--env-file env/.env.test

# 日常只改 json5 / workspaces / env：直接 up 即可，不必 rebuild
# 升 OpenClaw 版本：改 Dockerfile 的 ARG OPENCLAW_VERSION（及 compose args/image 标签）后重新 build
# 勿再在启动命令里 npm install -g openclaw（已烤进镜像）
```

验收：

```bash
# token 与 env/.env.prod 中 OPENCLAW_GATEWAY_TOKEN 一致
curl -sS http://127.0.0.1:18789/v1/models \
  -H "Authorization: Bearer $OPENCLAW_GATEWAY_TOKEN"
```

---

## 2. 启动 Python（tools + 门禁 + 控制台）

先配置环境（`env/.env.local` 或 `env/.env.prod`）：

- `MYSQL_*`：控制面库（表前缀 `agent_`）
- `AGENT_ADMIN_USERNAME` / `AGENT_ADMIN_PASSWORD`：控制台管理员
- `INTERNAL_GATEWAY_URL`：并网用 `http://openclaw-gateway:18789`
- `INTERNAL_GATEWAY_TOKEN`：与 Gateway token 一致
- `CONSOLE_SECRET_KEY`：控制台 Cookie 签名（生产用长随机串）

```bash
cp .env.example env/.env.local   # 按上表改值

docker compose --env-file env/.env.local \
  -f docker-compose.yml -f docker-compose.local.yml \
  up -d --build

# 生产示例：
# docker compose --env-file env/.env.prod \
#   -f docker-compose.yml -f docker-compose.prod.yml \
#   pull && up -d --no-build
```

验收：

```bash
curl -sS http://127.0.0.1:8000/v1/health
curl -sS http://127.0.0.1:8000/agent-gate/health
```

---

## 3. 管理页地址

| 入口 | 地址 |
|------|------|
| 控制台主页（输入 **G 或 A Token** 进入 API 管理） | **http://\<主机\>:8000/console** |
| 管理员 | 同页右上「管理员入口」；账密见 `AGENT_ADMIN_*` |

首次流程：管理员登录 → 成对签发 G+A → 用 G/A 进 API 页 → 为各 tool 填写完整上游 URL → 业务壳配置：

```bash
# Go 示例（指门禁，不是裸 :18789）
export OPENCLAW_GATEWAY_URL=http://<Python主机>:8000/agent-gate
export OPENCLAW_GATEWAY_TOKEN=<G>
export PANGBAO_API_TOKEN=<A>
```

### API 管理页：上游 URL（Python tools → Go history）

控制台每个 tool 填**完整 URL**。推荐上游基址（二选一，须 Python 容器可达）：

| 推荐 BASE | 说明 |
|-----------|------|
| `http://<Go主机>:9701` | Go **主网关** `gateway-service`，反代 `/device/history/api/*`，**无** App 用户 JWT |
| `http://history-service:9801` | 直连 history-service（须与 Python 同网或可解析） |

**不要**用 **gateway-app**（`:9702` / 多数需用户日更 JWT）当 Agent tools 上游。

**上游 Bearer**：对现网胖宝 history **留空**。该字段仅当上游真要 `Authorization: Bearer` 时填写；**不要**填终端用户 token。

| 控制台 tool | Method | 完整 URL（`{BASE}` + path） |
|-------------|--------|------------------------------|
| `history_create` | POST | `{BASE}/device/history/api/event/add` |
| `history_update` | POST | `{BASE}/device/history/api/event/update` |
| `history_delete` | POST | `{BASE}/device/history/api/event/delete` |
| `history_end_latest` | POST | `{BASE}/device/history/api/event/end-latest` |
| `history_filter` | GET | `{BASE}/device/history/api/filter` |
| `history_list` | GET | `{BASE}/device/history/api/list` |
| `history_options` | GET | `{BASE}/device/history/api/event/options` |
| `baby_profile` | GET | `{BASE}/device/history/api/birthday` |

示例：`http://192.168.1.10:9701/device/history/api/filter`。

---

## 目录

```
app/api/routes/          # health / tools / knowledge / gate / console
app/agent_console/       # DB、租户、塑形、上游、静态控制台
deploy/openclaw/         # Gateway 配置、workspaces、plugins
```

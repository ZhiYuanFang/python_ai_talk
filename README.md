# Python AI Talk

飞轮 / 塑形 History tools / 知识库 / **智能体门禁与控制台**。编排在 OpenClaw Gateway；对外请走本服务门禁。

## 架构（摘要）

| 角色 | 说明 |
|------|------|
| 门禁 `POST /agent-gate/v1/chat/completions` | 校验 **G Token** → 转发内部 Gateway |
| 控制台 `/console` | 签发 G↔A（1:1）、配置各 tool **完整 URL** |
| Tools `/v1/tools/*` | 按 **A Token** 路由上游并塑形；无默认 Go 域名 |
| Gateway 插件 | 仅 `toolsBaseUrl`，转发 `x-pangbao-api-token` |

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

要求：Node `>=22.22.3` 或 `>=24.15`；钉死发行版 `openclaw@2026.7.1-2`。

```bash
cd deploy/openclaw

# 编辑 openclaw.json5：
# - gateway.mode=local
# - gateway.auth.token 已引用 env OPENCLAW_GATEWAY_TOKEN（勿再写明文 REPLACE_ME）
# - agents 使用 list（勿用 entries）
# - 并网时 toolsBaseUrl 已为 http://python-ai-talk:8000/v1

export OPENCLAW_GATEWAY_TOKEN='与 Python INTERNAL_GATEWAY_TOKEN 一致'

cd plugins/pangbao-tools && npm install && npm run build && cd ../..
# 推荐（云机 / Linux）：
docker compose -f docker-compose.openclaw.yml up -d --force-recreate
# 本机直跑（可选）：
# openclaw gateway run --port 18789 --force
```

验收：

```bash
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

---

## 目录

```
app/api/routes/          # health / tools / knowledge / gate / console
app/agent_console/       # DB、租户、塑形、上游、静态控制台
deploy/openclaw/         # Gateway 配置、workspaces、plugins
```

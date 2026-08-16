## 1. OpenClaw 配置契约

- [x] 1.1 将 `deploy/openclaw/openclaw.json5` 的 `agents.entries` 改为 `agents.list`（`intent` / `clinic` / `care_alert` 带显式 `id`、workspace、tools.allow）
- [x] 1.2 workspace 改为容器绝对路径 `/openclaw/workspaces/...`；`toolsBaseUrl` 改为 `http://python-ai-talk:8000/v1`
- [x] 1.3 注释提醒：`gateway.auth.token` 须与 `INTERNAL_GATEWAY_TOKEN` / `OPENCLAW_GATEWAY_TOKEN` 一致（不写入真实 secret）

## 2. OpenClaw compose 并网

- [x] 2.1 `docker-compose.openclaw.yml`：`container_name: openclaw-gateway`；`networks` 加入 external `ai_agent_net`
- [x] 2.2 增加 volume `./plugins:/openclaw/plugins`（保留 json5、workspaces 挂载）
- [x] 2.3 compose 注释写明：先 `docker network create ai_agent_net`

## 3. Python compose 换网

- [x] 3.1 `docker-compose.prod.yml`：`go-ai-talk-net` → `ai_agent_net`
- [x] 3.2 `docker-compose.local.yml`：修正 networks 语法并改为 `ai_agent_net`
- [x] 3.3 `docker-compose.test.yml`：`go-ai-talk-test-net` → `ai_agent_test_net`

## 4. 文档

- [x] 4.1 更新 `README.md`：建网 → 启动 OpenClaw compose → 启动 Python；并网 URL 与勿公网裸放 18789
- [x] 4.2 （可选）`docs/deploy-guide.md` 中 `go-ai-talk-net` 相关段落改为 `ai_agent_net` / 本仓自管说明

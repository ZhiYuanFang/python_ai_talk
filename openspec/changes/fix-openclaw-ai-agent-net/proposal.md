## Why

云服务器上用 `docker compose -f docker-compose.openclaw.yml up -d` 启动 Gateway 时，配置校验失败（`agents: Invalid input`：钉死版 `openclaw@2026.7.1-2` 只认 `agents.list`，仓库草稿仍用 `agents.entries`）。同时 Python 与 OpenClaw 分属不同 Docker 网络、插件未挂载、`toolsBaseUrl` 指向容器内 `127.0.0.1`，即使配置修好也无法与本仓 tools/门禁互通。现将二者并入本仓自管网络 `ai_agent_net`，不再依赖 `go-ai-talk-net`。

## What Changes

- **BREAKING**：Python local/prod compose 的 Docker 网络从 `go-ai-talk-net` 改为 **`ai_agent_net`**（不再假设由 go_ai_talk 创建/共网）。
- **BREAKING**（OpenClaw 配置）：`deploy/openclaw/openclaw.json5` 的 `agents.entries` 改为符合 `2026.7.1-2` 的 **`agents.list`**（每项显式 `id` + workspace + tools.allow）。
- OpenClaw compose：固定 `container_name: openclaw-gateway`、加入 `ai_agent_net`、挂载 `plugins`（及既有 workspaces/json5）。
- 插件 `toolsBaseUrl` 默认改为 Docker DNS：`http://python-ai-talk:8000/v1`（与 `INTERNAL_GATEWAY_URL=http://openclaw-gateway:18789` 对称）。
- README / 部署说明：先 `docker network create ai_agent_net`，再 Gateway → Python；Go 经宿主机/内网门禁 URL 访问，不强制共 `ai_agent_net`。
- 测试 overlay：对称改为 `ai_agent_test_net`（与 prod 隔离命名）。

## Capabilities

### New Capabilities

- `openclaw-gateway-compose`：钉死版 Gateway 的 compose/配置契约（`agents.list`、插件卷、`toolsBaseUrl` DNS、加入 `ai_agent_net`、内部 token 对齐约定）。

### Modified Capabilities

- `docker-deployment`：本仓 Python 服务加入的外部网络由 `go-ai-talk-net` 改为 `ai_agent_net`；部署前提改为本仓/运维创建该网，不再依赖 go 微服务 compose 共网。

## Impact

- 文件：`deploy/openclaw/openclaw.json5`、`deploy/openclaw/docker-compose.openclaw.yml`、`docker-compose.prod.yml`、`docker-compose.local.yml`、`docker-compose.test.yml`、`README.md`；可选轻触 `docs/deploy-guide.md` 中网络段落。
- 运行时：云机需一次性 `docker network create ai_agent_net`（及 test 网若使用）；已挂在旧网上的容器需 recreate。
- Go：不改本仓 Go 代码；若仍用 `go-ai-talk-net` 找 Python，需改为宿主机映射端口或自行加入 `ai_agent_net`。
- 无 Python 业务 API 语义变更；不新增测试文件。

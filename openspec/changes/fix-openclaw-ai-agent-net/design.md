## Context

云机 Linux 上 OpenClaw 与 Python 分两个 compose 启动。Gateway 钉死 `openclaw@2026.7.1-2`：配置 schema 为 `agents.list`（`.strict()`），仓库草稿仍为 `agents.entries`，导致 `agents: Invalid input` 无法启动。即使修好 schema，compose 未挂插件、未共网，且 `toolsBaseUrl=http://127.0.0.1:8000` 在容器内无效。Python prod 当前依赖外部网 `go-ai-talk-net`（历史由 go 栈创建）；产品意图已变为「门禁对外、Gateway 对内」，Go 不必与 Python 共 Docker 网。

## Goals / Non-Goals

**Goals:**

- Gateway 配置通过 `2026.7.1-2` 校验并可持续运行。
- Python 与 OpenClaw 经 DNS 互通：`python-ai-talk` ↔ `openclaw-gateway`，共网 **`ai_agent_net`**。
- 本仓 local/prod/test overlay 与 openclaw compose 对齐该网名；文档写清建网与启动顺序。
- 插件可从容器加载；`toolsBaseUrl` / `INTERNAL_GATEWAY_URL` 使用服务名。

**Non-Goals:**

- 不改租户 G/A、门禁、塑形 History 业务逻辑。
- 不把 Go 强制并入 `ai_agent_net`；不修改 go_ai_talk 仓库。
- 不升级/换钉 OpenClaw 主版本（仍 `2026.7.1-2`）。
- 不编写自动化测试文件。

## Decisions

1. **网络名 `ai_agent_net`（test: `ai_agent_test_net`）**  
   - 替代 `go-ai-talk-net`，语义归属本智能体栈。  
   - **创建方式**：运维/文档先 `docker network create ai_agent_net`；Python 与 OpenClaw compose 均 `external: true` 加入，避免双 compose 抢 create。  
   - 备选（未采用）：由 openclaw compose 非 external 创建——Python 先起时会缺网。

2. **`agents.entries` → `agents.list`**  
   - 与包内 `AgentsSchema` 对齐；每项 `{ id, workspace, tools.allow }`；workspace 用 `/openclaw/workspaces/...`。  
   - 备选：降级 OpenClaw 到仍认 entries 的旧版——与钉死版本冲突，不采用。

3. **DNS URL**  
   - `toolsBaseUrl`: `http://python-ai-talk:8000/v1`  
   - `INTERNAL_GATEWAY_URL`: `http://openclaw-gateway:18789`（env 已基本如此）  
   - OpenClaw 固定 `container_name: openclaw-gateway`；Python 保持 `python-ai-talk`。  
   - 备选：宿主机 IP / `network_mode: host`——可通但不稳定、难文档化。

4. **插件卷**  
   - compose 增加 `./plugins:/openclaw/plugins`；json5 保持相对路径 `./plugins/pangbao-tools`（cwd `/openclaw`）。  
   - 宿主机需已 build 插件 `dist`（README 保留 build 步骤）。

5. **Go 访问路径**  
   - 经宿主机映射 `http://<host>:8000/agent-gate`（或反代），不依赖与 Python 共网。

6. **local.yml 网络块**  
   - 一并修正为合法的 `networks: { ai_agent_net: { external: true, name: ai_agent_net } }` 并挂到服务（当前写法残缺）。

## Risks / Trade-offs

- [旧网残留] 云机仍有容器挂在 `go-ai-talk-net` → recreate 到新网；文档注明。  
- [先起后建网] 未 create 网则 compose 失败 → README 第一步建网。  
- [18789 暴露] `--bind lan` + ports 映射可能对公网开放 → README 强调安全组只放行 8000、勿裸放 Gateway。  
- [token 未对齐] json5 `REPLACE_ME` 与 `INTERNAL_GATEWAY_TOKEN` 不一致 → 配置注释提醒，不在本 change 自动写 secret。  
- [文档滞后] `docs/deploy-guide.md` 仍提 go 网 → 本 change 至少改 README；deploy-guide 关键网络段可选轻改。

## Migration Plan

1. 云机：`docker network create ai_agent_net`（已存在则跳过）。  
2. 合并配置与 compose 变更后：`cd deploy/openclaw && docker compose -f docker-compose.openclaw.yml up -d --force-recreate`。  
3. Python：`--env-file env/.env.prod -f docker-compose.yml -f docker-compose.prod.yml up -d`（需已改网）。  
4. 验收：容器内/同网 `wget`/`curl` 互通；宿主机 `curl :18789/v1/models` 与 `:8000/v1/health`。  
5. 回滚：恢复旧 json5/compose 与 `go-ai-talk-net`（若仍存在）；否则临时用宿主机 IP URL。

## Open Questions

- 无阻塞项。test 网命名采用 `ai_agent_test_net`（已在 proposal 锁定）。

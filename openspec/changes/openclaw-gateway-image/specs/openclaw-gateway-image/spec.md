## ADDED Requirements

### Requirement: OpenClaw Gateway 预装镜像

系统 SHALL 提供 `deploy/openclaw/Dockerfile`，在镜像构建阶段安装钉死版本的 OpenClaw CLI（默认 `2026.7.1-2`，可通过 build ARG 覆盖）。镜像启动时 MUST 直接运行 Gateway（例如 `openclaw gateway --port 18789 --bind lan`），MUST NOT 在容器启动命令中执行 `npm install -g openclaw`。

#### Scenario: 构建产物含 openclaw

- **WHEN** 在 `deploy/openclaw` 执行针对该 Dockerfile 的 `docker compose build`（或等价 `docker build`）
- **THEN** 构建成功且镜像内可调用 `openclaw` CLI
- **AND** 安装版本为约定的钉死版本（默认 `2026.7.1-2`）

#### Scenario: 启动不再 npm install openclaw

- **WHEN** 审查 `docker-compose.openclaw.yml` 的服务启动命令与 Dockerfile `CMD`/`ENTRYPOINT`
- **THEN** 其中 MUST NOT 包含对 `npm install -g openclaw` 的调用
- **AND** 启动路径 MUST 启动 Gateway 监听约定端口（18789）

### Requirement: compose 构建并运行预装镜像

`deploy/openclaw/docker-compose.openclaw.yml` SHALL 通过 `build`（context 为 `deploy/openclaw`）构建 Gateway 服务镜像，并继续支持 `--env-file` 注入 `OPENCLAW_GATEWAY_TOKEN` 与 LLM API Key；SHALL 继续挂载 `openclaw.json5`、`workspaces`、`plugins`。网络与对外端口约定 MUST 与现网一致（`ai_agent_net`、宿主映射 `18789`）。

#### Scenario: env-file 启动

- **WHEN** 运维执行 `docker compose --env-file env/.env.prod -f docker-compose.openclaw.yml up -d`（工作目录为 `deploy/openclaw`）
- **THEN** 服务使用已构建的预装镜像启动
- **AND** 容器进程环境可获得 env 文件中的 Gateway token 与 LLM key（经 compose `environment` 透出）

### Requirement: README 说明镜像构建与日常启动

根 `README.md` 中 OpenClaw 启动一节 SHALL 说明：先 `build` 再 `--env-file` `up`；SHALL 区分「改 Dockerfile/版本需 rebuild」与「仅改 json5/workspaces/env 无需 rebuild」。MUST NOT 将「每次 up 时 npm install -g openclaw」表述为推荐启动方式。

#### Scenario: README 含 build 与 up

- **WHEN** 运维按 README 启动 OpenClaw Gateway
- **THEN** 文档给出 `docker compose … build`（或等价）与带 `--env-file` 的 `up` 命令
- **AND** 文档说明日常 recreate 不应再触发 openclaw 的 npm 全局安装

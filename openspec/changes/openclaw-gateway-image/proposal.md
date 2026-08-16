## Why

OpenClaw Gateway 当前用裸 `node` 镜像，在容器 `command` 里每次 `npm install -g openclaw@…`，`--force-recreate` 或重建容器都会重新下载，启动极慢。需要把钉死版本的 OpenClaw 写入镜像，启动只跑 gateway，并更新 README 说明后续如何 build/up。

## What Changes

- 新增 `deploy/openclaw/Dockerfile`：基于 Node 24，构建时安装 `openclaw@2026.7.1-2`（ARG 可钉版本）。
- 更新 `docker-compose.openclaw.yml`：`build` + 本地镜像名；**去掉**启动时 `npm install`；`command`/`CMD` 仅启动 `openclaw gateway`。
- 保留现有 volume（`openclaw.json5`、workspaces、pangbao-tools）与 `--env-file` 密钥注入。
- 更新根 `README.md` §1：先 `build`、再 `--env-file` `up`；说明改版本需 rebuild，改 json5/env 不必 rebuild。
- **不**在本变更解决 Unknown model / deepseek-provider 认模（可另开 change）。
- **不**强制推 ACR（文档可提可选 tag/push，非必须）。

## Capabilities

### New Capabilities

- `openclaw-gateway-image`: OpenClaw Gateway 以预装 CLI 的 Docker 镜像交付；compose 构建/启动约定与 README 运维说明。

### Modified Capabilities

- （无）不修改产品 API / 门禁行为 Requirement。

## Impact

- 文件：`deploy/openclaw/Dockerfile`、`deploy/openclaw/docker-compose.openclaw.yml`、`README.md`
- 运维：首次需 `compose build`；之后日常 `up` 不再拉 npm openclaw
- 运行时：版本仍钉 `2026.7.1-2`；网络/env/插件挂载路径不变

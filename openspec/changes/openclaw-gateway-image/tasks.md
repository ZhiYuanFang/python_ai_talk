## 1. Dockerfile

- [x] 1.1 新增 `deploy/openclaw/Dockerfile`：`FROM node:24.19.0-bookworm`；`ARG OPENCLAW_VERSION=2026.7.1-2`；`RUN npm install -g openclaw@${OPENCLAW_VERSION} --allow-scripts`；`WORKDIR /openclaw`；`CMD` 启动 `openclaw gateway --port 18789 --bind lan`（中文注释说明用途）

## 2. Compose

- [x] 2.1 更新 `docker-compose.openclaw.yml`：`build.context` 指向本目录；设置本地 `image` 名（含版本标签）；移除 command 内 `npm install -g openclaw`；启动仅跑 gateway（或依赖 Dockerfile CMD）
- [x] 2.2 保留 env 透出、volumes、ports、`ai_agent_net`；顶部注释改为「先 build 再 up」

## 3. README

- [x] 3.1 改根 `README.md` §1：配置 `env/.env.prod` → build 插件（若需要）→ `docker compose … build` → `--env-file … up -d`
- [x] 3.2 注明：升 OpenClaw 版本改 Dockerfile ARG 后须 rebuild；只改 json5/workspaces/env 不必 rebuild；勿再推荐启动时 npm install openclaw

## 4. 校验

- [x] 4.1 `openspec validate openclaw-gateway-image --strict`

## Context

`docker-compose.openclaw.yml` 使用 `node:24.19.0-bookworm`，启动命令内 `npm install -g openclaw@2026.7.1-2`，每次 recreate 重复下载。密钥已由 `deploy/openclaw/env` + `--env-file` 注入；json5/workspaces/plugins 仍 volume 挂载。运维要求启动快、版本仍钉死。

## Goals / Non-Goals

**Goals:**

- 构建时安装 OpenClaw，容器启动只执行 gateway。
- compose 通过 `build` 产出可复用本地镜像；README 写清 build / up / 何时 rebuild。
- 保留 env 注入与现有 volume、网络、端口约定。

**Non-Goals:**

- 修复 `Unknown model` / 安装 deepseek-provider / 改 agents.defaults.model。
- 强制接入 ACR CI（可选文档一句即可）。
- 把 pangbao-tools 或 json5 烤进镜像（继续 volume，便于改配置不 rebuild）。

## Decisions

1. **自建 Dockerfile，不用「仅官方镜像、本仓无 Dockerfile」作为唯一路径**  
   - 理由：钉死 `2026.7.1-2`、与现网 Node 基线一致、命令与挂载可控。  
   - 备选：官方 GHCR tag——若 tag 不全或工作目录约定不同，增加运维不确定性。

2. **`ARG OPENCLAW_VERSION=2026.7.1-2` + `RUN npm install -g`**  
   - 升版改 ARG/compose build-arg 后 `compose build`。  
   - 启动命令：`openclaw gateway --port 18789 --bind lan`（与现 CLI 一致）。

3. **compose：`build.context: .`（deploy/openclaw）+ `image: openclaw-gateway:2026.7.1-2`（或带本地前缀）**  
   - 去掉 command 中的 npm install；可用 `command` 覆盖或依赖 Dockerfile `CMD`。  
   - 继续 `environment` + 文档要求 `--env-file env/.env.prod`。

4. **README**  
   - 步骤：配置 env →（可选）build pangbao-tools → `compose build` → `compose --env-file … up -d`。  
   - 明确：改 OpenClaw 版本 / Dockerfile → rebuild；只改 json5、workspaces、env → 无需 rebuild。

## Risks / Trade-offs

- [首次 build 仍慢] → 可接受；之后 up 快；可用 build cache。  
- [镜像与 volume 内插件路径] → 保持 `WORKDIR /openclaw` 与现 volume 一致。  
- [忘记 rebuild 却以为升了版] → README 写明版本钉在 Dockerfile。

## Migration Plan

1. 提交 Dockerfile + compose + README。  
2. 云机：`cd deploy/openclaw && docker compose --env-file env/.env.prod -f docker-compose.openclaw.yml build && up -d`。  
3. 回滚：恢复旧 compose（运行时 npm install）或沿用旧镜像 tag。

## Open Questions

- 无（认模问题另案）。

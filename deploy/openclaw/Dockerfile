# OpenClaw Gateway 预装镜像
# 业务说明：构建时钉死安装 openclaw CLI，容器启动不再 npm install，避免每次 recreate 重新下载。
# 配置 / workspaces / 本仓插件仍由 compose volume 挂载，改 json5 不必 rebuild。
FROM node:24.19.0-bookworm

# 钉死发行版；升版改此 ARG 后执行 compose build
ARG OPENCLAW_VERSION=2026.7.1-2

# 全局安装 OpenClaw（含 lifecycle scripts，与官方安装约定一致）
RUN npm install -g "openclaw@${OPENCLAW_VERSION}" --allow-scripts

WORKDIR /openclaw

# 默认启动 Gateway：LAN 绑定供并网；鉴权与 LLM key 由运行时 env 注入
CMD ["openclaw", "gateway", "--port", "18789", "--bind", "lan"]

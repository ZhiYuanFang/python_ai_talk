# OpenClaw Gateway 预装镜像
# 业务说明：构建时钉死安装 openclaw CLI；启动经 entrypoint 为三 agent 种子 models.json + DeepSeek auth。
# 配置 / workspaces / 本仓插件仍由 compose volume 挂载，改 json5 不必 rebuild；改 entrypoint/种子须 rebuild。
FROM node:24.19.0-bookworm

# 钉死发行版；升版改此 ARG 后执行 compose build
ARG OPENCLAW_VERSION=2026.7.1-2

# 全局安装 OpenClaw（含 lifecycle scripts，与官方安装约定一致）
RUN npm install -g "openclaw@${OPENCLAW_VERSION}" --allow-scripts

WORKDIR /openclaw

# 可提交的 DeepSeek catalog 种子（apiKey 仅为 env 名 marker）
COPY seed/models.json /openclaw/seed/models.json
# 启动前 bootstrap，再 exec CMD/compose command
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
# 默认启动 Gateway：LAN 绑定供并网；鉴权与 LLM key 由运行时 env 注入
CMD ["openclaw", "gateway", "--port", "18789", "--bind", "lan"]

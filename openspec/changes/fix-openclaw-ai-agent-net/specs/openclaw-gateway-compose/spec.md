## ADDED Requirements

### Requirement: OpenClaw agents.list 配置契约
钉死发行版 `openclaw@2026.7.1-2` 的 Gateway 配置 MUST 使用 `agents.list`（数组，每项含显式 `id`），MUST NOT 使用已失效的 `agents.entries` 对象映射。列表 MUST 至少包含 `intent`、`clinic`、`care_alert` 三个 agent，各自绑定对应 workspace 与 tools.allow。

#### Scenario: 配置通过校验
- **WHEN** 使用仓库 `deploy/openclaw/openclaw.json5` 启动 `openclaw gateway`（含 compose 路径）
- **THEN** 配置校验 MUST NOT 因 `agents` 报 `Invalid input`，Gateway 进程可持续运行

#### Scenario: HTTP model 路由仍按 agent id
- **WHEN** 调用方以 `openclaw/intent`（或 clinic / care_alert）作为模型路由标识
- **THEN** Gateway MUST 能解析到 `agents.list` 中对应 `id` 的 agent

### Requirement: OpenClaw 与 Python 共网 ai_agent_net
`deploy/openclaw/docker-compose.openclaw.yml` MUST 将 Gateway 服务加入外部网络 `ai_agent_net`，且 MUST 设置 `container_name: openclaw-gateway`，以便 Python 侧 `INTERNAL_GATEWAY_URL=http://openclaw-gateway:18789` 可解析。

#### Scenario: 同网 DNS 可达
- **WHEN** Python 容器与 OpenClaw 容器均已加入 `ai_agent_net` 并运行
- **THEN** 从 Python 容器解析主机名 `openclaw-gateway` MUST 成功，且可访问其 Gateway HTTP 端口

### Requirement: 插件卷与 toolsBaseUrl
OpenClaw compose MUST 挂载宿主机 `./plugins` 至容器内 `/openclaw/plugins`。插件配置中的 `toolsBaseUrl` MUST 指向 Docker DNS `http://python-ai-talk:8000/v1`（并网部署），MUST NOT 默认使用容器回环 `http://127.0.0.1:8000/v1` 作为生产/云机并网路径。

#### Scenario: 插件目录可见
- **WHEN** Gateway 容器启动且配置了 `plugins.load.paths` 指向 `./plugins/pangbao-tools`
- **THEN** 容器内该路径 MUST 存在（来自挂载），而非因未挂卷而缺失

#### Scenario: tools 打到 Python 服务名
- **WHEN** 插件发起 tools HTTP 请求且使用仓库默认并网配置
- **THEN** 请求基址 MUST 为 `http://python-ai-talk:8000/v1`（或等价服务名解析到 Python 容器）

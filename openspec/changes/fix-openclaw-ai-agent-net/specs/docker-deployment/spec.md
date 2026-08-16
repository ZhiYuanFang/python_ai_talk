## MODIFIED Requirements

### Requirement: Docker Compose 配置
系统 SHALL 通过本仓库 `docker-compose.yml` 与 overlay（local/test/prod）定义 python-ai-talk 服务；local/prod 服务 MUST 加入外部 Docker 网络 **`ai_agent_net`**（由运维或文档步骤预先 `docker network create`，不再依赖 go_ai_talk 的 `go-ai-talk-net`）。OpenClaw Gateway 侧车 compose 亦 MUST 加入同一 `ai_agent_net`，以便与 Python 经服务名互通。

#### Scenario: 本地开发环境
- **WHEN** 已创建 `ai_agent_net` 且执行本仓 local overlay 启动命令
- **THEN** python-ai-talk 服务启动，并加入 `ai_agent_net` 网络

#### Scenario: 与 OpenClaw 并网
- **WHEN** python-ai-talk 与 `openclaw-gateway` 均加入 `ai_agent_net`
- **THEN** 双方 MUST 能通过容器服务名互相解析（`python-ai-talk`、`openclaw-gateway`）

#### Scenario: 环境变量注入
- **WHEN** docker compose 启动
- **THEN** python-ai-talk 服务从环境变量获取配置（含 `INTERNAL_GATEWAY_*`、`MYSQL_*`、`CONSOLE_SECRET_KEY` 等）

#### Scenario: Volume 挂载
- **WHEN** docker compose 启动
- **THEN** Chroma 等数据目录按 compose 配置挂载到容器

### Requirement: 生产环境配置
系统 SHALL 在 `docker-compose.prod.yml` 中提供 python-ai-talk 的生产 overlay：使用 registry 镜像，并加入外部网络 **`ai_agent_net`**（MUST NOT 再要求 `go-ai-talk-net`）。

#### Scenario: 生产镜像
- **WHEN** 启动生产环境
- **THEN** python-ai-talk 使用 `${REGISTRY}/python-ai-talk:${IMAGE_TAG}` 镜像

#### Scenario: 生产网络
- **WHEN** 启动生产环境
- **THEN** python-ai-talk 加入 `ai_agent_net` 外部网络

## ADDED Requirements

### Requirement: 测试环境网络命名
测试 overlay MUST 使用外部网络 **`ai_agent_test_net`**（与生产 `ai_agent_net` 隔离），MUST NOT 继续要求 `go-ai-talk-test-net` 作为本仓默认测试网名。

#### Scenario: 测试网隔离
- **WHEN** 使用 `docker-compose.test.yml` 启动测试栈
- **THEN** python-ai-talk-test 加入 `ai_agent_test_net`

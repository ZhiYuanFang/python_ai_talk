## Why

OpenClaw Gateway 侧车目前只注入 `OPENCLAW_GATEWAY_TOKEN`，缺少上游 LLM API Key；Go 经 `x-openclaw-model` 注模后，Gateway 无法用本机密钥调用 DeepSeek 等提供商。运维需要与 Python 一致的 `env/.env.prod|test` 注入方式，且真实密钥不得进入 Git。

## What Changes

- 新增 `deploy/openclaw/env/`：可提交的 `.env.example`；本地/运维持有的 `.env.prod`、`.env.test`（gitignore）。
- 从仓库根 `env/.env.prod` **复制**已有 LLM API Key（及与门禁对齐的 Gateway token）填入 OpenClaw `.env.prod`（实现阶段执行；制品中不写真实密钥）。
- 更新 `docker-compose.openclaw.yml`：通过 `--env-file` / `env_file` 将 token 与 LLM key 注入 `openclaw-gateway` 容器；版本仍钉死 `openclaw@2026.7.1-2`。
- 更新根 `README.md` §1：启动 Gateway 改为使用 `deploy/openclaw/env/.env.*`，不再仅靠 `export OPENCLAW_GATEWAY_TOKEN`。
- **不**删除或改动 Python 侧 LLM key / `llm_client`（飞轮与隐式采纳仍依赖）。
- **不**升级 OpenClaw 发行版。

## Capabilities

### New Capabilities

- `openclaw-gateway-env`: OpenClaw 侧车独立 env 文件、gitignore、compose 注入 LLM/Gateway 密钥，以及 README 启动约定。

### Modified Capabilities

- （无）本变更不修改既有能力的行为 Requirement；仅新增 Gateway 部署配置约定。

## Impact

- 文件：`deploy/openclaw/env/*`、`deploy/openclaw/docker-compose.openclaw.yml`、`.gitignore`、`README.md`
- 运行：重启 OpenClaw 容器后进程可见 `DEEPSEEK_API_KEY` 等；Python 栈不变
- 安全：真实 `.env.prod`/`.env.test` 不得提交；仅 example 进库

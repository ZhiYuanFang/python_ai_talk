## ADDED Requirements

### Requirement: OpenClaw Gateway 独立 env 目录

系统 SHALL 在 `deploy/openclaw/env/` 提供可提交模板 `env/.env.example`，以及运维使用的 `env/.env.prod` 与 `env/.env.test`。真实密钥文件 MUST NOT 被 Git 跟踪（与根目录 `env/.env.prod` / `env/.env.test` 同等忽略约定）。`env/.env.example` MUST 列入版本库且 MUST NOT 含真实 API Key。

#### Scenario: example 可提交且无真密钥

- **WHEN** 审查 `deploy/openclaw/env/.env.example`
- **THEN** 文件存在于仓库中，并列出至少 `OPENCLAW_GATEWAY_TOKEN` 与 `DEEPSEEK_API_KEY` 占位项
- **AND** 文件中 MUST NOT 出现可用的真实密钥值

#### Scenario: prod/test env 被忽略

- **WHEN** 运维在 `deploy/openclaw/env/` 创建 `.env.prod` 或 `.env.test` 并填入密钥
- **THEN** `.gitignore`（或等价规则）MUST 使这些文件不被 `git add` 纳入版本库

### Requirement: 从 Python 生产 env 对齐 OpenClaw 密钥

实现 OpenClaw `env/.env.prod` 时，系统运维流程 SHALL 从仓库根 `env/.env.prod` 复制已配置的 LLM API Key（至少 `DEEPSEEK_API_KEY`；根文件中若存在 `GLM_API_KEY`、`SILICONFLOW_API_KEY`、`MODELSCOPE_API_KEY` 等亦须复制）。`OPENCLAW_GATEWAY_TOKEN` MUST 与 Python 门禁所用内部 Gateway token（根 env 中 `INTERNAL_GATEWAY_TOKEN`，或已存在的 `OPENCLAW_GATEWAY_TOKEN`）一致。可提交制品 MUST NOT 写入这些真实值。

#### Scenario: prod 对齐复制

- **WHEN** 按本变更 tasks 生成 `deploy/openclaw/env/.env.prod`
- **THEN** 其中 LLM 相关键值与根 `env/.env.prod` 对应键一致
- **AND** `OPENCLAW_GATEWAY_TOKEN` 与 Python `INTERNAL_GATEWAY_TOKEN`（或根文件中的 `OPENCLAW_GATEWAY_TOKEN`）一致

### Requirement: compose 将 env 注入 Gateway 容器

`deploy/openclaw/docker-compose.openclaw.yml` SHALL 支持经 `--env-file`（指向 `deploy/openclaw/env/.env.prod` 或 `.env.test`）启动，并将 Gateway 鉴权 token 与 LLM API Key 注入 `openclaw-gateway` 服务进程环境。OpenClaw npm 包版本 MUST 仍为 `2026.7.1-2`。

#### Scenario: 容器可见 DEEPSEEK_API_KEY

- **WHEN** 使用 `--env-file env/.env.prod` 启动 `docker-compose.openclaw.yml` 且文件含非空 `DEEPSEEK_API_KEY`
- **THEN** `openclaw-gateway` 容器进程环境 MUST 包含该 `DEEPSEEK_API_KEY`
- **AND** 容器仍安装并运行 `openclaw@2026.7.1-2`

### Requirement: README 以 env-file 方式启动 OpenClaw

根 `README.md` 中「启动智能体（OpenClaw Gateway）」一节 SHALL 指导使用 `deploy/openclaw/env/` 下的 env 文件（`docker compose --env-file …`），MUST NOT 将「仅 export OPENCLAW_GATEWAY_TOKEN、无 LLM key」表述为推荐生产启动方式。SHALL 注明 Python 侧 LLM key 仍保留给飞轮/tools，与 OpenClaw env 分离。

#### Scenario: README 推荐 env-file

- **WHEN** 运维按 README §1 启动 OpenClaw
- **THEN** 文档给出的推荐命令包含指向 `env/.env.prod`（或 `.env.test`）的 `--env-file`
- **AND** 文档说明需配置 LLM API Key（非仅 Gateway token）

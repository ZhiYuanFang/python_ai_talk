## 1. Gitignore 与 example

- [x] 1.1 在 `.gitignore` 增加 `deploy/openclaw/env/.env.prod`、`deploy/openclaw/env/.env.test`、可选 `deploy/openclaw/env/.env.local`（勿忽略 `.env.example`）
- [x] 1.2 新增 `deploy/openclaw/env/.env.example`：占位 `OPENCLAW_GATEWAY_TOKEN`、`DEEPSEEK_API_KEY`、`GLM_API_KEY` 及可选硅基/魔搭键；中文注释说明用途与「勿提交真密钥」

## 2. 从根 env 生成 OpenClaw env（不提交）

- [x] 2.1 读取根 `env/.env.prod`，写入 `deploy/openclaw/env/.env.prod`：复制 LLM 相关键；`OPENCLAW_GATEWAY_TOKEN` 对齐 `INTERNAL_GATEWAY_TOKEN`（或根已有 `OPENCLAW_GATEWAY_TOKEN`）
- [x] 2.2 若存在根 `env/.env.test`，同样生成 `deploy/openclaw/env/.env.test`；否则由 example 复制占位
- [x] 2.3 确认 `git status` 中上述 `.env.prod`/`.env.test` 未被跟踪

## 3. Compose 注入

- [x] 3.1 更新 `deploy/openclaw/docker-compose.openclaw.yml`：`env_file` 指向 `env/.env.prod`（或文档约定由 CLI `--env-file` + `environment` 显式透出 LLM keys）；保持 `openclaw@2026.7.1-2`
- [x] 3.2 注释标明：须与 Python `INTERNAL_GATEWAY_TOKEN` 一致；LLM key 供 Gateway 调上游，非门禁 G

## 4. README

- [x] 4.1 改根 `README.md` §1：推荐 `docker compose --env-file env/.env.prod -f docker-compose.openclaw.yml up …`；说明先填 `deploy/openclaw/env`
- [x] 4.2 注明 Python `env/.env.*` 的 LLM key 仍留给飞轮/tools，与 OpenClaw env 分离；版本仍钉 `2026.7.1-2`

## 5. 校验

- [x] 5.1 `openspec validate openclaw-gateway-env --strict`

## Context

OpenClaw Gateway 与 Python 分属两套 compose。Python 已用根目录 `env/.env.prod` 注入业务与飞轮 LLM key；Gateway compose 仅有 `OPENCLAW_GATEWAY_TOKEN`，进程内看不到 `DEEPSEEK_API_KEY` 等，导致 Go 注模后上游调用失败。运维希望 OpenClaw 侧镜像「独立 env 目录 + --env-file」习惯，并从现有 `env/.env.prod` 拷贝 API Key，避免手填两套不一致密钥。

## Goals / Non-Goals

**Goals:**

- `deploy/openclaw/env/.env.example` 可提交，列出 Gateway token 与 LLM 相关键。
- `.env.prod` / `.env.test` 存在于该目录、填入与根 `env/.env.prod` 对齐的密钥值，且被 gitignore（与根 `env/` 同等待遇）。
- compose 把上述变量注入 `openclaw-gateway` 容器环境。
- README 启动命令改为 `--env-file deploy/openclaw/env/.env.prod`（或相对 `deploy/openclaw` 的路径）。
- 版本保持 `openclaw@2026.7.1-2`。

**Non-Goals:**

- 删除或弱化 Python 侧 LLM key / `llm_client`。
- 升级 OpenClaw npm 包或改 agents/json5 模型目录。
- 把 OpenClaw 并入 Python 主 compose 栈。
- 在任何可提交文件中写入真实 API Key。

## Decisions

1. **独立目录 `deploy/openclaw/env/`，不复用根 `env/.env.prod` 作为 compose env_file**  
   - 理由：根 env 含 MySQL/控制台等大量无关变量；Gateway 只需 token + LLM keys，职责分离。  
   - 备选否决：`env_file: ../../env/.env.prod` — 易误注入、难维护 test/prod 差异。

2. **实现时从根 `env/.env.prod` 复制键值到 OpenClaw `.env.prod`**  
   - 至少：`DEEPSEEK_API_KEY`、`GLM_API_KEY`（及根文件中已有的 `SILICONFLOW_*` / `MODELSCOPE_*` 若存在则一并复制）。  
   - `OPENCLAW_GATEWAY_TOKEN`：取自根 env 的 `INTERNAL_GATEWAY_TOKEN`（门禁与 Gateway 须一致）；若根已有 `OPENCLAW_GATEWAY_TOKEN` 则优先用该键。  
   - `.env.test`：结构同 example；可从 `env/.env.test` 同名键复制（若无则留占位）。

3. **compose 双轨注入**  
   - CLI：`docker compose --env-file env/.env.prod -f docker-compose.openclaw.yml …`（替换 `${VAR}`）。  
   - 服务级 `env_file: - env/.env.prod` 或 `environment` 显式列出 LLM keys，保证进入容器进程（OpenClaw 读进程 env，不只宿主机 shell）。

4. **gitignore**  
   - 增加 `deploy/openclaw/env/.env.prod`、`deploy/openclaw/env/.env.test`（及可选 `.env.local`）；**不**忽略 `.env.example`。

5. **密钥不进制品**  
   - proposal/design/tasks/example 仅占位符；真实值只写在被忽略的本地文件，apply 时从根 `env/.env.prod` 读取写入。

## Risks / Trade-offs

- [两份密钥漂移] → README 注明「改 Python LLM key 时同步 OpenClaw env」；本轮用复制降低首次不一致。  
- [仅补 key 仍 Unknown model] → 本轮不升级版本；若验收仍失败，另开 change 查模型目录。  
- [误提交密钥] → gitignore + 只提交 example；apply 后 `git status` 确认 `.env.prod` 未 staged。

## Migration Plan

1. 提交 example、compose、README、gitignore。  
2. 在部署机生成 `.env.prod`（从根 env 复制）。  
3. `docker compose --env-file env/.env.prod -f docker-compose.openclaw.yml up -d --force-recreate`。  
4. 回滚：去掉 `env_file`/恢复旧 README，或清空 LLM env 后重建（行为退回「无 key」）。

## Open Questions

- 无（版本与 Python 留 key 已由探索拍板）。

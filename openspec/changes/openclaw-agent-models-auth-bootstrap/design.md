## Context

OpenClaw `@2026.7.1-2` 多 agent（`intent` / `clinic` / `care_alert`）下，chat completions 解析 LLM 依赖：

1. agent 目录 `models.json`（catalog / baseUrl）
2. 同目录 `openclaw-agent.sqlite` auth store（上游 API key）

现场已证实：

- Gateway 启动可写出 `{"providers":{}}`（约 22 字节）；该文件存在时比「缺文件」更糟，会挡住 catalog。
- `models.mode: "replace"` 且 resolve 为空时，ensure **刻意**写空文件；本仓须保持 **`merge`**。
- 仅 json5 `models.providers` 未能阻止空文件再现；手工非空 `models.json` 后错误变为 `missing-provider-auth`。
- 容器 `DEEPSEEK_API_KEY` 长度正常（约 35），但 care_alert chat **不**用该 env 作为该 agent 的有效凭证。
- 本镜像 CLI **不**接受 `paste-token --agent`；应用 `OPENCLAW_AGENT_DIR=.../agents/<id>/agent` + `paste-api-key`（DeepSeek `sk-` 形）。

现有 compose **不**挂 `~/.openclaw`，每次 recreate 状态丢失 → 必须 **启动时 bootstrap**。

## Goals / Non-Goals

**Goals:**

- recreate / 冷启动后，三 agent 均有非空 DeepSeek catalog（至少含 `deepseek-v4-flash`）。
- 同一启动路径把 `DEEPSEEK_API_KEY` 写入三 agent 的 auth store（无交互）。
- `POST /v1/chat/completions` 以 `model=openclaw/care_alert`（及 intent/clinic）在 Gateway token 正确时，不再因 Unknown model / missing-provider-auth 失败（上游 LLM 业务错误另论）。
- 种子与脚本可提交；无明文 key。

**Non-Goals:**

- 不改 Go 注模 / Python agent-gate 转发契约。
- 不引入 named volume 作为本轮必选项（可选后续优化）。
- 不升级 OpenClaw 主版本；不修上游 ensure 空 plan 的根因（用部署绕过）。
- 不实现密钥轮换自动化；不把 key 写入 git。

## Decisions

### D1: Entrypoint 启动前种子 models.json（覆盖空毒丸）

- **选择**：`docker-entrypoint.sh`（或等价）在 `exec openclaw gateway ...` **之前**，对 `intent`/`clinic`/`care_alert`：`mkdir -p` + 复制仓库种子；若目标为缺失、或内容为 `{"providers":{}}` / 等价空 providers，则覆盖。
- **备选**：仅依赖 json5 `models.providers` → 现场已失败。  
  启动后异步覆盖 → 竞态，首次请求仍可能 Unknown。  
  named volume 保留状态 → 运维更重，且首次仍要种子。
- **理由**：merge + resolve 空 → ensure **skip**，不覆盖非空种子；必须在 gateway 写盘逻辑之前种好。若 ensure 仍以 replace 写空，则保持 json5 `mode: merge` 并在 README 强调勿改 replace。

### D2: 种子内容与 json5 对齐，apiKey 仅 marker

- 种子含 `deepseek` provider：`baseUrl`、`api: openai-completions`、`models[]` 含 `deepseek-v4-flash`（可含 pro 与 json5 一致）。
- `apiKey` 写 **`DEEPSEEK_API_KEY`**（env 名 marker），禁止明文。
- 文件路径建议：`deploy/openclaw/seed/models.json`，镜像 `COPY` 或 compose 挂载只读后由 entrypoint 复制到 agentDir。

### D3: 用 CLI + OPENCLAW_AGENT_DIR 灌 auth，不用手写 sqlite

- 对每个 agent：`printf '%s\n' "$DEEPSEEK_API_KEY" | OPENCLAW_AGENT_DIR=/root/.openclaw/agents/<id>/agent openclaw models auth paste-api-key --provider deepseek`（以镜像 `--help` 为准；若无 `paste-api-key` 则改用 help 中的等价子命令）。
- **备选**：手写 auth-profiles.json → 字段易错（如 `api_key` vs `key`），且新版以 sqlite 为准。  
  仅靠进程 env → 已证伪对 care_alert chat 不够。
- 若 `DEEPSEEK_API_KEY` 为空：entrypoint **失败退出**（或明确 warn 后仍启动但 README 标明 chat 会 401）——推荐 **非空才灌 auth，空则 stderr 警告并继续启动 Gateway**（便于只测进门），但 spec 验收要求生产 env 非空。

### D4: 保持 compose 注入 LLM env；json5 登记保留

- 继续 `--env-file` + `DEEPSEEK_API_KEY` 等；`openclaw.json5` 的 `models.providers` / `primary` / pin 策略不变。
- entrypoint 替换当前仅 `command: ["openclaw","gateway",...]`：Dockerfile `ENTRYPOINT` + `CMD` 传 gateway 参数，或 compose `entrypoint` 指向脚本。

### D5: 不强制 volume

- 每次启动重跑 bootstrap 即可幂等（paste 重复写入可接受；若 CLI 拒绝对已有 profile，先 `auth list` 有则 skip，实现时以最小逻辑为准）。

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| CLI 子命令名与文档不一致 | 实现任务第一步在镜像内 `openclaw models auth --help`；任务写「以 help 为准」 |
| ensure 在启动后仍覆盖种子为空 | 保持 `merge`；验收检查启动后 `models.json` 仍非空；若仍被盖，改为 gateway 后短循环重种（次选） |
| paste 写入默认 agent 而非 care_alert | 强制 `OPENCLAW_AGENT_DIR`；list 三份目录验证 |
| 密钥进 shell 历史 | 仅管道 stdin；禁止 `echo key` 进 compose/README 示例明文 |
| rebuild 负担 | 种子若 volume 挂载可不 rebuild；脚本进镜像则改 bootstrap 需 rebuild |

## Migration Plan

1. 合并本变更 → 云上 `compose build` → `--env-file ... up -d --force-recreate`。
2. 验收：`models.json` 非空；`auth list` 有 deepseek；curl `openclaw/care_alert` 不再 Unknown / missing-provider-auth。
3. 回滚：恢复旧 Dockerfile/compose command，recreate；行为回到当前故障态（预期）。

## Open Questions

- `paste-api-key` 在 `2026.7.1-2` 是否存在：apply 时以容器 help 锁定；若仅有 `add`/`login`，design 允许改用非交互等价路径并在 tasks 勾选说明。
- 是否同时 bootstrap `main` agent：本轮仅三业务 agent；若 Gateway 内部依赖 main catalog，apply 时若再现 Unknown 再补 main。

## Why

生产 Gateway 在 `force-recreate` 后仍对 `openclaw/care_alert`（及同类 agent）返回 `Unknown model: deepseek/deepseek-v4-flash`：启动时写出空的 `~/.openclaw/agents/<id>/agent/models.json`（`{"providers":{}}`），掏空 chat 模型目录；手工补全目录后变为 `missing-provider-auth`——进程虽有 `DEEPSEEK_API_KEY`，non-main agent 的 sqlite auth store 仍无 deepseek 凭证。仅靠 `openclaw.json5` 的 `models.providers` 登记无法在 recreate 后自愈，需部署侧持久 bootstrap。

## What Changes

- 为 `intent` / `clinic` / `care_alert` 提供可提交的 **DeepSeek `models.json` 种子**（仅 env 名 marker，无明文 key）。
- Gateway 容器 **entrypoint**：在 `exec openclaw gateway` 之前，将种子写入各 agent 目录；若已存在空 `providers:{}` 则覆盖为种子。
- 同一 entrypoint（或紧随其后的一次性脚本）：用进程内 `DEEPSEEK_API_KEY`，经 `OPENCLAW_AGENT_DIR` + `openclaw models auth paste-api-key --provider deepseek`（或本镜像 CLI 等价命令）写入各 agent auth store。
- 保持 `models.mode: "merge"`（禁止用 `replace` 在 resolve 为空时主动写回空文件）。
- README：说明 recreate 后自愈、手工探针、以及勿在 `models.json` 写明文 key。
- **不改** Go；**不改** Python agent-gate 契约；不强制挂 named volume（以 entrypoint 每次启动 bootstrap 为主）。

## Capabilities

### New Capabilities

- `openclaw-agent-runtime-bootstrap`: Gateway 启动时为三 agent 种子非空 models 目录，并从 `DEEPSEEK_API_KEY` 写入 per-agent DeepSeek auth，使 chat completions 在 recreate 后可用。

### Modified Capabilities

- （无；基线 v0.0.1 无对等 OpenClaw 运行时 bootstrap 需求；`openclaw-register-deepseek` / `pin-openclaw-deepseek-flash` 的 json5 约定保留并被本能力依赖。）

## Impact

- `deploy/openclaw/`：Dockerfile / entrypoint、`seed/`（或等价）models.json、compose `command`/`entrypoint`、README
- 运维：改 bootstrap 后需 **rebuild** 镜像（若种子打进镜像）或至少 recreate；日常改 json5 仍可只 recreate
- 安全：种子与脚本禁止提交明文 LLM key；已泄露的 key 须运维轮换（本变更不处理轮换流程）

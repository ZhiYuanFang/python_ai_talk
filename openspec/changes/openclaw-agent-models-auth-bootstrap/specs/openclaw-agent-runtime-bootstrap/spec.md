## ADDED Requirements

### Requirement: Gateway 启动为三 agent 种子非空 DeepSeek models.json

部署侧 OpenClaw Gateway 容器在启动 `openclaw gateway` 之前，MUST 为 `intent`、`clinic`、`care_alert` 三个 agent 目录写入非空的 `models.json`，其中 SHALL 包含 provider `deepseek` 以及模型 id `deepseek-v4-flash`（完整 ref 为 `deepseek/deepseek-v4-flash`）。种子中的 `apiKey` MUST 仅为环境变量名标记（如 `DEEPSEEK_API_KEY`），MUST NOT 包含明文密钥。若目标文件缺失，或内容为仅含空 `providers` 对象的毒丸文件，启动脚本 MUST 用种子覆盖。

#### Scenario: recreate 后 care_alert models.json 非空

- **WHEN** 运维对 Gateway 执行 force-recreate 且容器成功启动
- **THEN** `/root/.openclaw/agents/care_alert/agent/models.json` SHALL 存在且 `providers.deepseek.models` 中 SHALL 包含 id `deepseek-v4-flash`
- **AND** 该文件 MUST NOT 仅为 `{"providers":{}}`（或语义等价的空 providers）

#### Scenario: 种子无可提交明文 key

- **WHEN** 审查仓库内用于 bootstrap 的 `models.json` 种子文件
- **THEN** 文件中 MUST NOT 出现 DeepSeek 明文 API key（`sk-` 前缀密钥串）
- **AND** `apiKey` 字段 SHALL 为 env 名称标记

### Requirement: Gateway 启动将 DEEPSEEK_API_KEY 写入各 agent auth store

当进程环境变量 `DEEPSEEK_API_KEY` 非空时，Gateway 启动路径 MUST 在启动监听之前（或与种子同序、在接受业务 chat 之前）为 `intent`、`clinic`、`care_alert` 各自的 agent 目录写入 DeepSeek 提供商鉴权，使得 chat 路径可解析到 provider `deepseek` 的 API key。写入方式 SHALL 使用 OpenClaw CLI 官方鉴权子命令（优先 `models auth paste-api-key`），并通过 `OPENCLAW_AGENT_DIR`（或该发行版文档等价机制）指向对应 agent 目录；MUST NOT 依赖将明文 key 写入可提交的 git 文件。

#### Scenario: env 有 key 时 care_alert 不再 missing-provider-auth

- **WHEN** 容器已注入非空 `DEEPSEEK_API_KEY`，且 models 种子已就位，且 Gateway 鉴权 token 正确
- **AND** 客户端对 Gateway 调用 `POST /v1/chat/completions`，body `model` 为 `openclaw/care_alert`
- **THEN** 响应 MUST NOT 为 `authentication_error` / `missing-provider-auth`（因 care_alert 缺少 deepseek 凭证）
- **AND** 响应 MUST NOT 为因未知模型 `deepseek/deepseek-v4-flash` 导致的 `Unknown model`

#### Scenario: 按 agent 目录隔离写入

- **WHEN** bootstrap 为三个业务 agent 写入 DeepSeek auth
- **THEN** 每个 agent 的写入 MUST 使用各自的 `OPENCLAW_AGENT_DIR`（或等价）指向 `/root/.openclaw/agents/<id>/agent`
- **AND** MUST NOT 仅写入默认 agent 目录而期望 care_alert 自动继承（本发行版已证实不足）

### Requirement: 保持 merge 模式并文档化 recreate 自愈

`deploy/openclaw/openclaw.json5` 中 `models.mode` MUST 保持为 `merge`（或省略而默认为 merge），MUST NOT 在 resolve 为空时使用会主动写出空 `providers` 的 `replace` 作为本部署默认。README（或等价运维说明）SHALL 说明：改 bootstrap/种子后可能需要 rebuild；force-recreate 后应自愈；禁止在 agent `models.json` 中提交明文 key。

#### Scenario: 运维说明可复核

- **WHEN** 阅读仓库中 OpenClaw 部署 README 相关段落
- **THEN** 文档 SHALL 提及启动 bootstrap（models 种子 + DeepSeek auth）与 recreate 自愈
- **AND** SHALL 提醒勿将明文 LLM key 写入 seeds 或 git

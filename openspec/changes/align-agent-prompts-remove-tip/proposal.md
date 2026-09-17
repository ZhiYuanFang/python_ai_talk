## Why

Flutter 已砍 tip；Go 侧 tip 入口亦已下线，但 Python 仍保留 `app/tip` 与 `/v1/tip/stream`，形成死代码。同时各 agent 提示词结构不一、缺统一中文思考约束，care_alert 仍依赖外置 `prompt.json`；对外 SSE 若误用 `invoke` 假流式会损害体验。需要一次对齐：删 tip、提示词同构轨迹 `system.py`、中文思考、流式真流式，并写入全局约束防复发。

## What Changes

- **BREAKING（Python）**：删除 tip 模块与 `POST /v1/tip/stream`（及 tip 相关 schema/会话开场写入）；companion 仅服务 clinic。
- **Go 校对**：在 `d:\work\go_ai_talk` 确认 runtime 已无 tip（既有 change `remove-tip-and-clinic-feedback`）；若仍有残留则删除并保障 clinic/care-alert/intent 不受影响；清理本仓 `scripts/patch_go_*` 等 tip 补丁痕迹。
- **care_alert**：删除 `data/care_alert/prompt.json` 与 `prompt_store` 外置加载；文案内联到 `care_alert/.../prompts/system.py`（**以当前仓库 `prompt.json` 为准**）+ 中文思考约束；可去掉 `CARE_ALERT_PROMPT_DIR` 卷依赖。
- **提示词结构**：强制保留模块各有 `graphs/nodes/prompts/system.py`——`growth_trajectory`（已有）、`care_alert`、`clinic`、`feeding`、`shared`（覆盖 `needs_history` / `data_requirement`）；统一「内部思考（reasoning）须使用中文」及面向家长/结构化输出的中文要求。
- **流式约定**：对外 SSE/流式 HTTP 的主回答 LLM MUST `llm_client.stream`（禁止 invoke 完再整段当流）；内部短判定允许 invoke。
- **全局文档**：将上述 agent/提示词/流式约定写入 `openspec/project.md`，并摘要到 `AGENTS.md`；同步修正过时的 tip/通识向量库表述。

## Capabilities

### New Capabilities

- `llm-agent-prompt-conventions`: 每模块 `system.py`、中文思考/输出、对外流式必须真 stream 的工程约定（并落到 project.md）
- `care-alert-inline-system-prompt`: care_alert 静态 system 内联、无外置 prompt.json
- `retire-tip-python`: Python tip agent/API 退役

### Modified Capabilities

- `tip-generation`: 退役 tip 图与 `/v1/tip/stream`
- `tip-feedback`: 确认已无 tip feedback（与既有 retire 对齐，删除残留要求）
- `bestie-companion-persona` / `grounded-bestie-prompts`：去掉 tip 路径义务（若仍引用 tip）
- `langgraph-unified-stream` / `progressive-stream-thinking`：去掉 tip_graph 场景；保留 clinic/intent/care-alert/growth 流式约定
- `companion-session`: tip 开场不再写入会话
- `docker-deployment` / `env-config`: 去掉 care_alert prompt 卷必达与 tip 相关部署说明
- `code-organization-standard` 或通过新 capability 约束 prompts 目录：目录树去掉 tip，保留 feeding/clinic/shared/care_alert/growth_trajectory

## Impact

- **Python**：`app/tip/**`、`app/api/routes/tip.py`、routes 挂载、companion tip 写入、care_alert `prompt_store`/`prompt.json`、各模块 prompts、`openspec/project.md`、`AGENTS.md`、deploy/README
- **Go（`d:\work\go_ai_talk`）**：校对无 tip 业务入口；有残留则删；**不得**破坏 clinic WS、care-alert、intent
- **API**：**BREAKING** 移除 `/v1/tip/stream`；care_alert analyze 行为不变（仅 prompt 来源变更）
- **非目标**：不改意图 CRUD 主语义；不恢复通识/Q&A 飞轮；growth_trajectory 仅补齐文档/与全局约定一致（中文思考已在 system）

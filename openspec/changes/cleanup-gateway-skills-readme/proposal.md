## Why

`openclaw-gateway-direct` 已把产品编排迁到 OpenClaw Gateway，但 Python 仓仍残留 LangGraph/进程内 agent 时代的图节点、Care 算卡链路与过期 README，查阅成本高、易误当入口。需删死代码、把 Care/Intent 有效规则迁成 Gateway workspace skill，并用短对照 README 说明「以前只起 Python」与「现在先起 Gateway」的部署差。

## What Changes

- **BREAKING（Python）**：删除 Care 卡片算力（`generate_care_alerts` / analyze 链 / Care 飞轮）；卡片推理与出卡规则仅存于 Gateway `care_alert` workspace skill，经 `emit_care_cards` 结构化出卡。
- **BREAKING（Python）**：删除无入口的 Intent/Clinic 进程内编排（空 agents、空 graph 壳、`intent_pipeline`、图节点等）；先把**有效原则**提炼为 OpenClaw workspace skill（tool-calling，不照搬 LangGraph JSON 信封），再删代码。
- 保留并收束：`/v1/tools/*`（Intent/Clinic 飞轮、隐式判定、`emit_care_cards`）、`/v1/knowledge/*`、`/v1/health`、飞轮门面中 Intent/Clinic 仓。
- 新增 `deploy/openclaw/workspaces/{intent,clinic,care_alert}/`（AGENTS.md / skills）：适配 OpenClaw，禁止整段搬迁旧 classify JSON prompt。
- **重写 README**：短文；核心是 LangGraph→OpenClaw **部署对照表** + 最短启动/验收命令；不写云主机入门散文。
- **Go 审计与收尾**：核对 Intent/Clinic/Care 已走 Gateway；删除或掏空无调用方的 `PythonAIClient` 编排方法；compose/配置补齐 `OPENCLAW_GATEWAY_*`，避免仍暗示 `PYTHON_AI_TALK_URL` 为编排上游。

## Capabilities

### New Capabilities

- `gateway-workspace-skills`：Intent/Clinic/Care 的 OpenClaw workspace 规则与 skill 契约（tool 优先、NL 回复、Care 出卡权威）
- `post-gateway-cleanup`：Python 死代码删除边界与保留面（tools/知识库/飞轮）
- `deploy-readme-openclaw`：README 部署文档口径（LangGraph 旧法 vs OpenClaw 新法）

### Modified Capabilities

- （无直接改 `openspec/specs/v0.0.1.md` 已归档条目名；行为增量以本 change 新 capability 为准，收版时并入下一基线。）

## Impact

- **Python**：`app/feeding|clinic|care_alert` 大幅瘦身；`deploy/openclaw/workspaces`；`README.md`；可选标注 `docs/deploy-guide.md` 过期。
- **Go（兄弟仓）**：产品路径已切 Gateway；本 change 含审计任务 + 删除死客户端/配置对齐。
- **运维**：云上必须先跑 Gateway 再跑 Python tools；Go 配 `OPENCLAW_GATEWAY_URL`。
- **禁止**：生成测试文件。

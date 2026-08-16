## Why

`openclaw-three-agents` 只做到「去 LangGraph + 进程内迷你编排」，**并未**接入真实 OpenClaw Gateway，意图条件边仍在 Python。产品需要：编排权威在 Gateway、Go 只做业务壳（鉴权/额度/注 model）、Python 只保留飞轮等 tool 后端；并砍掉结构化意图信封、Care 飞轮与 Clinic 显式点赞，避免前端直打 Python、Go 沾飞轮。

## What Changes

- **BREAKING**：OpenClaw **Gateway 直接对外**成为 Intent / Clinic / Care Alert 的编排权威；删除 Python 进程内 `run_agent_steps` / `*_agent.py` 条件边编排与「OpenClaw 就绪」伪实现。
- **BREAKING**：Go（`go_ai_talk`）以 Gateway 客户端替换 `PythonAIClient` 对 `/v1/analyze|clinic|care-alert` 的调用；进 Gateway **前由 Go 注入 model**（额度/VIP 仍在 Go）。
- **BREAKING**：Intent 对 Go **只回自然语言 reply**；落库仅经 Gateway 调业务 tools（四写 REST + filter 等）；**删除**结构化意图契约（`target_type` / `events[]` / `need_confirm` 等及 Go 侧解析链）。
- **BREAKING**：废掉大半 FastAPI 产品入口（至少意图/陪伴编排路由）；Python 缩为飞轮（及可选知识）**tool 服务**；history tools 优先直打 Go，不必经 Python 转手。
- **BREAKING**：Go **与数据飞轮零关系**（不调、不转、不存飞轮）；飞轮 retrieve/record 仅 Gateway agent → 飞轮 tools。
- **BREAKING**：Care Alert **取消数据飞轮**（无 prompt/ledger/feedback 闭环）；仍为 Gateway agent + **结构化 tool 出卡片**；Go 可管日缓存展示，但不做飞轮转发；前端不直打 Python。
- **BREAKING**：Clinic **取消显式点赞**（删除 `/device/api/clinic/feedback` 及 Python `/v1/clinic/feedback`）；**仅保留** Clinic agent 回合内**隐式采纳** → 飞轮 tool。
- 澄清分轮：靠 Gateway **session**（映射原 `conversation_id`/device 线程），不再依赖 Python pending + `need_confirm` 布尔。
- 与进行中 change `openclaw-three-agents`：**继承** tip 删除、四 REST、top_k、飞轮门面等资产；**作废**其「进程内等价 loop 即 OpenClaw」结论；本变更完成后以本规格为准。

## Capabilities

### New Capabilities

- `openclaw-gateway-runtime`：真实 Gateway 编排权威；三 agent 分区与 tool ACL；Go 注 model；session 映射；废 Python 自编排
- `intent-reply-tools-only`：Intent 只经 tool 落库；对 Go 仅 NL reply；删除结构化意图信封
- `care-alert-gateway-cards`：Care Alert Gateway agent + 结构化出卡 tool；无 Care 飞轮；Go 日缓存无飞轮语义
- `flywheel-agent-only`：飞轮仅 Intent/Clinic 两仓；仅 agent→tool；Go 零飞轮；废 Clinic 显式反馈与 Care 飞轮路径

### Modified Capabilities

- `openclaw-three-agents`：修正为必须真实 Gateway；废进程内迷你图达标定义
- `hosted-flywheel-aggregate`：Care 仓移除；仅 intent + clinic；触发方仅为 Gateway agent
- `agent-business-tool-contract`：tools 由 Gateway 调用；写四 REST + 读 filter；Clinic/Care 禁写
- `intent-analysis` / `intent-stream-response` / `intent-python-history-crud`：**BREAKING** 产品入口改 Gateway；删除结构化响应契约
- `clinic-stream` / `clinic-consultation`：改 Gateway；废显式 feedback
- `env-config`：Go 侧 `OPENCLAW_GATEWAY_URL`；Python 不再作为意图内核入口；废 tip/废反馈类变量对齐
- `retire-tip-agent`：保持 tip 删除（若前序未收版则本变更验收仍要求 tip 不存在）

## Impact

- **Python**：删除大半 FastAPI 编排路由与 `shared/agents` 迷你 runtime；保留飞轮 HTTP tools（intent/clinic）；删除 care_alert 飞轮与 clinic 显式 feedback；可选知识检索 tool
- **Go**：`PythonAIClient`→Gateway 客户端；删意图 JSON 解析/落库二次路径；删 clinic/care 飞轮转发；Care 出卡读 tool result；配置注入 Gateway URL + per-run model
- **OpenClaw**：部署 Gateway；三 `agents.entries` + tool policy；workspace/skills
- **Flutter**：删除 clinic 显式点赞与 care 飞轮类反馈（若有）；Care ignore 若保留则仅本地/日缓存 UI
- **依赖**：真实 OpenClaw Gateway；禁止再以自写 step loop 冒充
- **非目标**：不恢复 tip SSE；不把飞轮做成租户 BYO；不强制同 PR 完成全部 Flutter UI 抛光（tasks 可分仓勾选）；禁止生成测试文件

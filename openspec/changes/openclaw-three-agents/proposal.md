## Why

LangGraph 编排过重，意图/陪伴/护理留意为迁就图状态与统一 SSE 付出了大量节点与条件边成本；产品未上线，可无历史兼容地改换技术选型。对外售卖需要：**三 Agent 可拆**（Intent 最可能单卖）、业务 API 可重绑、**分轮由外侧持有 conversation_id**、护城河为**我方托管聚合的数据飞轮**（用得越多越准）。现网 tip 前端已退役；点查只能播「最近一条」，无法回答「前两次分别在什么时候」。

## What Changes

- **BREAKING**：废弃 LangGraph 作为编排运行时；Python 侧先重构为 **OpenClaw 三 Agent 就绪结构**（Intent / Clinic / Care Alert），删除图节点/StateGraph/为 LangGraph 定制且不再需要的 API 与流式编排胶水。
- **BREAKING**：删除 **tip** 智能体全链路（Python `/v1/tip/*`、相关 graph/schema；Go `TipStream`/`TipCtrl`/`/device/tip/*` 及无用 tip feedback；Flutter 死代码 `TipRepository`/`HomeTipPanel`/`tip_provider`）。**保留** Flutter `widget_tip_*`（护理留意推桌面文案，非 tip agent）。
- **三 Agent 边界（不合并）**：
  - **Intent**：喂养 CRUD + 确认分轮 + 查记录；可写历史。
  - **Clinic**：仅聊天读信息；**禁止**挂 create/update/delete/end。
  - **Care Alert**：仅信息 → 卡片列表；无写库。
- **实施顺序**：① 先重构 Python（去 LangGraph、拆 tip、Agent/tool 边界、飞轮与读史语义）→ ② 再补齐/校对 Go 业务 REST 与语义 → ③ 删除 Go/Python 中仅为 LangGraph 匹配而存在、现已无调用方的 API。
- Intent **写**改绑 Go **四单动词 REST**（create/update/delete/end），Agent **不再依赖** `event/batch`（batch 可保留给非 Agent 调用或后续删除，本变更以 Agent 路径为准）。
- Intent **读**增强：`top_k`（默认 1）+ filter **按 start_time 倒序**取前 k 条；模板支持「前两次分别…」类播报（上限封顶，如 5）。
- 飞轮：**仅我方托管聚合**；三仓物理隔离；业务 tool URL 可配置，**飞轮基址不可 BYO**。Intent 飞轮存可移植结构（事件名/动作，不存跨租户 event_id）。`conversation_id` 仍由外侧持有。
- OpenClaw Gateway 替换编排进程为**目标架构**；本变更 Python 阶段完成 Agent/skill/tool 契约与去图化，使后续接入 Gateway 不再依赖 LangGraph。
- **生产配置**：重写 `env/.env.prod`（并同步 `.env.example` / `settings`）：删除 tip/LangGraph/未使用兄弟仓变量；增加业务 API 基址、飞轮锁定、top_k 等重构变量；**Go 侧生产域名赋值为** `https://www.pangbao.cuplay.top`（见 [胖宝官网](https://www.pangbao.cuplay.top/)）。保留现有 LLM/ACR/Redis 等仍需要的密钥与镜像变量（不改密钥值，除非运维另发）。

## Capabilities

### New Capabilities

- `openclaw-three-agents`: 三 Agent 产品与运行时边界、可拆售卖、Clinic/Care 只读 ACL、外侧 conversation_id
- `hosted-flywheel-aggregate`: 我方托管聚合飞轮；三仓隔离；飞轮 API 锁定；Intent 可移植缓存键
- `agent-business-tool-contract`: BYO/自有 Go 业务 tool 最小面（写四 REST + filter/options/profile 等）
- `history-read-topk`: 查记录 top_k 语义与多条模板播报
- `retire-tip-agent`: 删除 tip agent 全链路；明确保留 widget tip

### Modified Capabilities

- `langgraph-intent-graph` / `langgraph-clinic-graph` / `langgraph-unified-stream`: **BREAKING** 废止以 LangGraph StateGraph 为编排权威的要求，改为 OpenClaw/非图 Agent 运行时
- `intent-analysis` / `intent-stream-response` / `intent-python-history-crud`: 写路径改四 REST；去掉对 batch 的依赖；流式若保留须不依赖 LangGraph custom stream
- `intent-history-query` / `history-query` / `history-filter-api` / `http-api-alignment`: filter 排序与 top_k；对齐单动词写接口
- `companion-session` / `tip-generation` / `tip-feedback` / `clinic-tip-event-dictionary-channel`: tip 开场与 tip 共享会话要求删除或收窄为仅 clinic
- `clinic-stream` / `clinic-consultation`: 明确只读 tool；无 tip 合成轮
- `code-organization-standard` / `python-runtime`（若基线有技术栈表述）: 技术栈从 LangGraph 改为 OpenClaw 编排；目录可保留 feeding/clinic/care_alert，删除 tip 模块
- `env-config`: 生产 `.env.prod` 适配 OpenClaw 三 Agent；Go 基址 `https://www.pangbao.cuplay.top`；删除无用变量；飞轮/业务 URL 分离

## Impact

- **Python**：删除 `app/tip/**`、LangGraph 图与依赖；重构 intent/clinic/care_alert 为 Agent+tool；http_client 改四 REST + 增强 filter；飞轮服务化边界（先进程内实现经稳定接口，基址锁定）；`settings` + `env/.env.prod` / `.env.example`
- **Go（`go_ai_talk`，本仓 tasks 列校对清单，实现可跨仓）**：补齐/对齐 add/update/delete/end-latest 与 Agent 语义；filter `ORDER BY start_time DESC`；删除 tip 宿主与反代；可选废弃 Agent 对 batch 的依赖
- **Flutter（`flutter_ai_talk`）**：删除 tip SSE 死代码；保留 widget tip
- **依赖**：移除 `langgraph`；引入/对接 OpenClaw（Python 阶段可先无 Gateway，保留接口形状）
- **非目标**：不做租户本地飞轮；不合并三 Agent；不恢复 tip SSE；不把飞轮写入对方业务 API；不在 OpenSpec 正文中粘贴真实密钥

## Context

Python AI Talk 现为 FastAPI + 四套 LangGraph（intent / clinic / tip / care_alert），经 httpx 调 Go history-service。Intent 写库走 `POST .../event/batch`；读史走 filter，但播报层每事件只留最近一条。飞轮分三套（`feeding_intents` / `qa_fast_path` / care_alert ledger+prompt），均在 Python 进程内。Flutter tip SSE 已退役；companion 会话曾被 tip 与 clinic 共享。

产品未上线；对外售卖要：三 Agent 可拆、业务 API 可重绑、conversation_id 外侧持有、飞轮仅我方托管聚合。编排目标换 OpenClaw。实施顺序：**先 Python 重构 → 再补 Go → 删仅为 LangGraph 服务的废 API**。

## Goals / Non-Goals

**Goals:**

- 去掉 LangGraph 编排与 tip agent；保留 Intent / Clinic / Care Alert 三边界与各自飞轮。
- Python 形成 OpenClaw 就绪的 Agent + Tool 形状（技能、tool 调用、分轮 pending、飞轮读写点）。
- Intent 写改四单动词 REST；读支持 `top_k` 多条模板。
- 飞轮经稳定接口、基址锁定我方；Intent 缓存可移植（名/动作，非跨租户 id）。
- 列出 Go/Flutter 删除与补齐清单，供跨仓落地。

**Non-Goals:**

- 本变更不要求一次上线完整 OpenClaw Gateway 集群运维（可先进程内 Agent runtime，契约对齐）。
- 不合并三 Agent；不做租户本地飞轮；不恢复 tip SSE。
- 不强制删除 Go `event/batch`（Agent 停用即可）；不做跨仓 Flutter/Go 的强制同 PR（tasks 分仓勾选）。
- 禁止生成测试文件。

## Decisions

### D1：实施顺序 Python → Go → 删废 API

- **选择**：先在本仓去图、拆 tip、换 http 客户端与读史语义、飞轮接口化；再按契约补 Go 排序/字段；最后删 tip 与 LangGraph 专用无调用方 API。
- **替代**：先改 Go 再改 Python → Agent 仍绑 batch/图，废代码更久。
- **原因**：产品未上线，Python 是编排痛点；契约先稳定，Go 补齐有明确 checklist。

### D2：三 Agent 不合并；Clinic/Care 无写 tool

```
Intent:  dictionary, create, update, delete, end, filter(+top_k), latest?
Clinic:  filter/list, baby.profile, knowledge — NO writes
Care:    filter/list, baby.profile — NO writes; output cards
Flywheel:* → 锁定我方（三仓隔离）
```

- **替代**：Clinic+Care 合并 → 与「可拆售卖 / Intent 单卖」冲突；曾 intent↔clinic 合并已证明有害。

### D3：写路径四 REST，读路径一个增强 filter

- 写：`add` / `update` / `delete` / `end-latest`（对齐现有 Go path）；多事件由 Agent 多次调用，先 end 后其余。
- 读：`filter` + `top_k`/`limit` + **`ORDER BY start_time DESC`**；不另拆四个读 REST。
- **替代**：继续 batch → 与 tool 粒度/对外授权不符。

### D4：飞轮托管聚合 + 可移植 Intent 键

- 闭环点：Intent 确认且写成功；Clinic 隐式采纳；Care ignore/follow_up。
- 存储可先仍为本机 Chroma/Redis/文件，但 **仅经 `flywheel.retrieve` / `flywheel.record_outcome` 访问**，配置项 `flywheel_base_url` 默认本服务且 **不允许被业务 BYO 覆盖**。
- Intent document：规范化说法 + `{op, events[{name, action, ...}], top_k?}`；执行前用对方 `options` 解析 id。

### D5：分轮仍外侧 conversation_id

- pending 澄清存 Agent 侧（可 Redis 化，按 cid）；请求带回 cid 与现网一致。
- 不强制接入方实现 pending；不把飞轮主键绑在 cid 上。

### D6：删除 tip；保留 widget tip

- 删 Python tip 模块与路由；Go TipStream/TipCtrl/gateway tip 反代；Flutter `tip_repository`/`tip_provider`/`home_tip_panel`。
- **保留** `widget_tip_*` 与 care_alert → 桌面文案。

### D7：LangGraph 相关 API / 代码清理范围

删除或停用（无调用方或仅为图流式胶水）：

- `langgraph` 依赖、`StateGraph`、各 `*_graph.py`、`with_node_thinking` 若仅服务图 custom stream。
- 统一 `astream(custom+updates)` 若改为 OpenClaw/原生 SSE 后无用的适配层。
- tip 全套；Intent 对 `batch_history_events` 的调用路径。

保留：FastAPI 对外 `/v1/analyze/intent`、`/v1/clinic`、`/v1/care-alert/*` 等 **产品入口**（内部改为调 Agent runtime，而非图）；知识管理 API 若仍独立则保留。

### D8：`top_k` 读史

- 分类输出 `events[].top_k`（int，默认 1，上限 5）；「前两次」→ 2；「上一次」→ 1 + 可配合 `ignore_time_range`。
- `speak_history`（或后继 read skill）按时间序取 k 条，模板列举，禁止再捏成单条「上一次」除非 k=1。

### D9：生产 `env/.env.prod` 与 Go 域名

- **Go 生产基址**：`https://www.pangbao.cuplay.top`（[胖宝官网/入口](https://www.pangbao.cuplay.top/)，无尾斜杠写入变量值）。
- **赋值约定**：
  - `GO_API_BASE_URL=https://www.pangbao.cuplay.top` — Agent 业务 tool 默认可重绑基址
  - `HISTORY_SERVICE_URL=https://www.pangbao.cuplay.top` — 与现网 http_client 路径 `/device/history/api/...` 经网关同源；若部署证明必须走 Docker 内网名，可另增 `HISTORY_SERVICE_INTERNAL_URL` 作覆盖，但 **prod 默认写公网 Go 域名**（按产品负责人要求）
- **删除（Python 未使用或重构后无意义）**：`DEVICE_SERVICE_URL`、`VOICE_SERVICE_URL`（应用代码未调用；画像走 history birthday）；任何 tip/LangGraph 专用变量（若曾引入）
- **新增/补齐**：
  - `FLYWHEEL_BASE_URL=` 空表示进程内我方飞轮；非空则必须为我方可控 URL，**无**客户 BYO 文档项
  - `HISTORY_READ_TOP_K_MAX=5`
  - Care Alert 飞轮目录与阈值（与 `.env.example` 对齐：`CARE_ALERT_*`）
  - 可选 `OPENCLAW_GATEWAY_URL`（Gateway 就绪前可空）
- **保留**：`REGISTRY`/`IMAGE_TAG`/`ACR_*`、`REDIS_URL`、`LOG_LEVEL`、LLM 密钥与 base URL、`CHROMA_*`/`EMBEDDING_MODEL`、`CLEAR_FEEDING_INTENTS_ON_STARTUP`
- **同步**：`.env.example`、`settings.py`、`docker-compose.yml` environment 注入键与三层同名；**不在 OpenSpec 正文写入真实密钥**

目标 `env/.env.prod` 结构（密钥处保留原文件已有值，apply 时原样保留）：

```
# 镜像 / Redis / LOG / LLM 密钥…（保留）
GO_API_BASE_URL=https://www.pangbao.cuplay.top
HISTORY_SERVICE_URL=https://www.pangbao.cuplay.top
FLYWHEEL_BASE_URL=
HISTORY_READ_TOP_K_MAX=5
CARE_ALERT_PROMPT_DIR=/app/data/care_alert
CARE_ALERT_EXAMPLES_MAX_CHARS=1200
CARE_ALERT_FLYWHEEL_REWRITE_EVERY=20
CARE_ALERT_FLYWHEEL_REWRITE_MIN_INTERVAL_S=3600
CARE_ALERT_FLYWHEEL_MIN_EVIDENCE=2
CARE_ALERT_LEDGER_MAX_LINES=500
CARE_ALERT_FLYWHEEL_TTL_DAYS=7
OPENCLAW_GATEWAY_URL=
# 已删除：DEVICE_SERVICE_URL、VOICE_SERVICE_URL
```

## Risks / Trade-offs

- **[OpenClaw 接入时序]** Python 先去图但 Gateway 未就绪 → 中间态用薄 Agent loop（LLM + tool 调用）→ 契约不变，后续换 Gateway。
- **[BYO 字典不一致]** 全局飞轮若存 event_id → 串租户 → 强制可移植名/动作 + 执行时解析。
- **[filter 按 id 排序]** 「前两次」不准 → Go 必须改 start_time 倒序（Python 阶段可客户端再排序作过渡，tasks 要求 Go 补齐）。
- **[跨仓删除 tip 不同步]** App 仍打 tip → 404 → Flutter 死代码与 Go 删除列入 tasks，验收勾选。
- **[batch 仍被他处调用]** Agent 停用即可；全删 batch 另议，避免拖垮本变更。
- **[公网 HISTORY_SERVICE_URL]** 容器经公网回打网关可能增延迟或鉴权差异 → 若上线实测失败，用内网名覆盖并保留 `GO_API_BASE_URL` 给对外文档/BYO 模板；默认仍按负责人要求写公网域名。

## Migration Plan

1. **Python**：删 tip → 抽 tool 客户端（四写 + filter）→ Intent 写改单调用 → top_k 播报 → 飞轮门面 → 拆 LangGraph 换 Agent runtime → 更新 `project.md` 技术栈表述。
2. **Go**：filter 排序；校对四写与 batch 子项语义差；删 tip 宿主与反代。
3. **Flutter**：删 tip SSE 死代码。
4. **回滚**：未上线，以 git revert 变更分支即可；无生产数据迁移。

## Open Questions

- ~~OpenClaw 具体发行版 / Python 绑定方式（Gateway 内嵌 vs 侧车）在 apply 首周 spike 锁定。~~
  **已关闭（apply）**：本期采用**进程内 Agent loop**（`app/shared/agents/runtime.py` + 各 `*/agents/*_agent.py`），契约对齐 OpenClaw 技能/tool；`OPENCLAW_GATEWAY_URL` 预留为空，后续可换 Gateway 而不改产品入口。
- Go `event/batch` 是否在同一波跨仓删除，还是仅文档标明 Agent 禁用（默认：**本变更不删 batch 路由**）。
- Clinic 对外 SSE 帧格式是否与现网完全一致（默认：**保持现有 thinking/answer/done 产品契约**，实现换引擎）。
- 公网 `https://www.pangbao.cuplay.top` 是否已反代 `/device/history/api/*` 至 history-service；若否，apply 时需运维确认或临时改回 Docker 内网名（`GO_API_BASE_URL` 仍可保留公网）。

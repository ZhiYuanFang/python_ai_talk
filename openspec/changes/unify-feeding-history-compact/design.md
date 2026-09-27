## Context

拉史已统一走 `app.shared.graphs.nodes.fetch_history` + filter API，但注入/播报形态分叉：

| 模块 | 现状 |
|------|------|
| care_alert | `history_compact`：日×名·时刻·总量 + legend |
| growth_trajectory | 原事件 JSON `[:20]`；plan 仅条数 |
| clinic | `slim_history_events_for_prompt` + 汇总时 `build_daily_history_summary` |
| intent daily | `build_daily_history_summary`（分类极少写出 `history_mode=daily`） |

Flutter 解析 care-alert items 时 **缺 `eventId` 丢弃**，且按 `eventId` 与推演关闭集合过滤；故留意仍须 legend。

## Goals / Non-Goals

**Goals:**

- 共享聚合函数落在 `app/shared/`，算法 = 现 care_alert compact（本变更不改规则）。
- care_alert / growth_trajectory generate / clinic 有史归纳 / intent daily 消费同一 `history_text` 形态。
- care_alert 继续用 legend 回填 `eventId`。
- 删除 `build_daily_history_summary`。
- 窗长 / limit 仍由各 Agent 的 `DataRequirement` 决定。

**Non-Goals:**

- 不优化聚合算法（留给后续变更）。
- 不统一窗长（留意 2 天 vs 轨迹 7 天等维持现状）。
- 不改 intent `point` 模板；不改分类是否产出 `history_mode=daily`。
- 不改 `prior_feedback` / 画像 / qa / Go·Flutter 契约。
- 不生成测试文件。

## Decisions

### D1: 提函数，不新建「拉+聚合」门面

- **选择**：把 `build_care_alert_history_prompt_blocks`（及组行辅助）挪到 `app/shared/`（去 care_alert 命名，如 `build_feeding_history_prompt_blocks` → `(history_text, legend)`）。
- **不选**：共享 async「拉史+聚合」门面——窗长已分治，拉史节点已共享；本变更只统一形态。
- **兼容**：care_alert 旧路径改为 re-export 或直接改 import；删除模块内重复实现。

### D2: 消费方怎么用 legend

| 消费方 | history_text | legend |
|--------|--------------|--------|
| care_alert | 必用 | 必用（回填 eventId + 软兜底） |
| growth_trajectory generate | 必用（替 JSON） | 不用 |
| clinic needs_history | 必用（替 daily + slim JSON 史块） | 不用 |
| intent daily | 必用（替 build_daily_*） | 不用（勿念给家长） |
| intent point | 不动 | — |

### D3: clinic 有史路径整段改 compact

- **选择**：`needs_history=true` 时用户消息的喂养史块改为共享紧凑文本；不再拼 `build_daily_history_summary`，也不再塞 slim JSON 明细块。
- **取舍**：点查相对口吻（刚刚 / N分钟前）在 clinic 有史路径弱化；时钟仍以聚合行 HH:mm 呈现。后续可再为点查恢复 relative slim，但不复活 `build_daily_history_summary`。

### D4: growth_trajectory plan_next

- **选择**：`generate` 必须注入 compact；`plan_next` 可将「仅条数」升级为注入同一 `history_text`（或短预览），避免规划与生成所见史形态不一致。
- **不改**：`prior_feedback` / `qa_so_far`。

### D5: 删除薄汇总

- 两处调用（clinic、intent daily）改完后删除 `build_daily_history_summary`。
- 保留 `slim_history_events_for_prompt` / `format_history_time`（其它点查路径可能仍用；若本变更后 clinic 不再引用 slim，其它引用保留即可）。

### D6: 现状窗长对照（不改数值）

| Agent | 窗长 | limit（约） |
|-------|------|-------------|
| care_alert | `last_n_days(2)` | 60 |
| growth_trajectory | `last_n_days(7)` | 40 |
| clinic | `judge_data_requirement` | 动态 |
| intent read | 分类 unix 窗 / ignore_time_range | intent.limit 默认 20 |

## Risks / Trade-offs

- [intent daily 几乎不触发] → 本变更只对齐预留支路；启用需另改分类 prompt（Non-Goal）。
- [clinic 点查失去 relative slim] → 接受；可后续加回 slim 而不恢复 daily 函数。
- [compact 行变长（7 天窗）] → 轨迹/clinic token 上升；属既有窗长选择，非本变更引入的新窗。
- [搬家漏改 import] → tasks 列全量引用点；实现后全仓搜 `build_care_alert_history` / `build_daily_history_summary`。

## Migration Plan

1. 新增 shared 模块并迁入算法（行为字节级保持）。
2. 依次改 care_alert → growth_trajectory → clinic → intent daily。
3. 删除 `build_daily_history_summary` 与 care_alert 旧文件（或薄包装一层 deprecate 删除）。
4. 手工：留意仍出带 eventId 的 items；轨迹/clinic 提示可见紧凑行；intent point 回归。

Rollback：恢复 shared 迁出前各模块原注入方式（git revert 本变更即可）。

## Open Questions

- 无（explore 已拍板）。后续算法优化另开 change。

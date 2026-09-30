## Context

意图图路径：`match_intent_cache` →（miss）`classify_intent` → 确认/执行/`speak_history`。缓存命中整包复用 `events[]`，`collect_event_items` 用 `start_time or now`，故「记录5点吃了120」命中「记录吃了120」种子时会落到当下时间。点查「上次」在 `speak_history` 取最新行（含进行中），旧 Scenario「Timer in progress」按最新开始播报。运营缺少对 `feeding_intents` 的可视化纠错。兄弟仓 voice-service 已持有 `PythonAIClient` 与 `/voice/admin/api/*` 反代。

约束：Python 不直连 DB；中文注释；禁止测文件；不恢复 tip/外置 prompt 飞轮；本期不同步 MySQL。

## Goals / Non-Goals

**Goals:**

- 点查「上次」跳过进行中，优先已完成；仅进行中时固定话术。
- 缓存命中后规则槽位覆盖 clock/qty；多钟点×单条 events 强制 LLM。
- 同叶多时刻 create 可验收（prompt + 确认 + batch）。
- Hub：查看/批量上传/删除 Chroma 意图向量（Go 页 + Python API）。

**Non-Goals:**

- MySQL 种子表/训练表与静默双写、LoRA 导出。
- 槽位覆盖用小模型（一期仅规则）。
- 降低确认门槛（LLM 路径仍默认确认）。
- 改 Go history filter 协议（选行在 Python）。

## Decisions

### D1：上次选行在 Python `speak_history`

对点查结果按事件跳过 `endTime` 无效的进行中行，取下一笔已完成；父事件在展开叶子集合上同样规则。仅剩进行中：`目前仅找到一条记录，是{相对时间}发生，正在进行中`。不新增 Go `excludeOpen`。

**备选**：Go filter 加 flag — 推迟，改动面大且本仓已够用。

### D2：`overlay_slots` 插在缓存命中之后

```
match_intent_cache --hit--> overlay_slots --> route
         | miss
         v
   in_progress_probe → classify...
```

覆盖只改 `quantity` / `start_time`（非计时 create 时 `end_time=start_time`），不改 `op`/`event_id`。clock 支持「N点」「N点M分」与半角/全角「H:MM」。qty 须「毫升/吃了」等上下文，并屏蔽钟点片段（含冒号）。`len(clocks)≥2` 且 `len(events)==1` → 清除免确认命中，图继续走 classify。

**备选**：规则直接拆 N 条 events — 否决，超出「覆盖」、易错。

### D3：写缓存/种子剥绝对时间

`intent_cache_store.add` 与 admin bulk：create 骨架 payload MUST NOT 固化绝对 `start_time`（或写入后剥离），避免冻死第一次确认时刻；quantity 可作默认，本轮抽取优先覆盖。

### D4：同叶多时刻靠 classify + 确认，不靠覆盖扩行

Prompt 明确：一句 N 次喂养 → N 条 create；允许同 `event_id`；create 填钟点 unix。确认文案列出每条时间与毫升。多钟点对单条缓存仍走 D2 降级。

### D5：Admin 权威只在 Chroma；Go 无表

- Python：`GET/POST/DELETE`（或等价）管理 `feeding_intents`（list 分页、bulk upsert、delete by id）。
- Go：`intent-vector-admin.html` + `admin-modules.js`；voice `/voice/admin/api/intent-vectors/*` → `PythonAIClient`。
- 删除以 Chroma 成功为准。

**备选**：MySQL 双写 — 本期明确不做。

### D6：跨仓任务标注

本仓 `tasks.md` 列 Python 任务；Go 任务单独一节「兄弟仓 go_ai_talk」，实现时在 go 仓落地，本仓用文档约定契约。

## Risks / Trade-offs

- [规则漏抽钟点] → 仍用 now；可后续加小模型兜底，本期接受。
- [多钟点强制 LLM 增确认回合] → 正确性优先于免确认。
- [Chroma list 无富查询] → Admin 先全量/简单分页；量大再优化。
- [Hub 误删向量] → 删除前展示 document+payload；无回收站（可后续）。
- [旧「Timer in progress」话术变更] → **BREAKING** 相对旧产品文案；以新 Scenario 为准。

## Migration Plan

1. 先上 Python：选行 + overlay + prompt/确认 + admin API。
2. 再上 Go Hub 页与代理。
3. 运营批量灌无钟点骨架种子。
4. 回滚：关 overlay 节点或 feature 开关（可选，非必须）；Chroma 种子可 Admin 删。

## Open Questions

- Admin API 路径前缀最终用 `/v1/admin/intent-cache/` 还是 `/v1/feeding/intent-cache/`（实现时与现有路由风格对齐即可）。
- Go Hub 是否需 Admin JWT 以外的额外角色限制（沿用现有 voice admin 即可）。

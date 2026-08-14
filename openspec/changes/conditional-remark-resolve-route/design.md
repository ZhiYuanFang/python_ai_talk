## Context

当前 `route_after_classify` 恒返回 `resolve_remark_event`；节点用 `_unresolved_slots` 无槽位则 `{}`。语义上「字典未命中才反查」已在节点内，但图边与流式 thinking 仍每轮经过反查节点。用户要求：条件进路由；`resolve_remark_event` 只做反查。

相关实现：`intent_graph.py`、`resolve_remark_event.py` 的 `_unresolved_slots`。行为基线以已落地的 `post-classify-remark-resolve` 为准（分类后备注反查、禁止新建事件类型）。

## Goals / Non-Goals

**Goals:**

- `route_after_classify`：有「名称非空且 event_id 空」的槽位 → `resolve_remark_event`；否则与 `route_after_remark_resolve` 相同分支（`end` / `speak_history` / `execute_history_crud`）。
- 未定槽位检测与路由、节点共用同一实现，避免漂移。
- 反查节点假定由路由门控进入；专注 Go 备注反查与写回/消歧/无法识别。

**Non-Goals:**

- 不改备注反查 HTTP 参数、聚合、多命中消歧、零命中无法识别语义。
- 不恢复分类前备注探针；不引入 `is_new_event`；不写测试。

## Decisions

### 1. 条件放在 `route_after_classify`，复用 `route_after_remark_resolve` 的落点

- **选择**：有未定槽位 → `resolve_remark_event`；否则直接调用与 `route_after_remark_resolve` 相同的判定（或抽 `_route_after_intent_ready`），映射表同时包含反查与确认/执行/查记录目标。
- **理由**：图边表达业务分支；无未定名称时不跑 thinking 包装节点。
- **备选**：节点内空返回（现状）→ 拒绝，因每轮空访。
- **备选**：分类节点写 `needs_remark_resolve` 标志 → 可做，但与扫描 intent 槽位重复；优先共享函数扫描。

### 2. 抽出 `has_unresolved_event_slots` / `unresolved_event_slots`

- **选择**：从 `resolve_remark_event` 导出（或移到小型 feeding 工具模块）供路由与节点使用；判定仍为顶层与 `events[]`「有 name 无 id」。
- **理由**：单一真相源。
- **备选**：路由内复制逻辑 → 禁止。

### 3. 节点内防御性早退保留

- **选择**：无槽位仍可 `return {}`，但不作为主路径依赖。
- **理由**：缓存直达等边界、误连边时安全。

### 4. 条件边映射表扩大

- **选择**：`classify_intent` 的 conditional_edges 目标含 `resolve_remark_event`、`end`、`speak_history`、`execute_history_crud`（与反查后一致）。
- **理由**：跳过反查时须能直达落库/查记录/END。

## Risks / Trade-offs

- [路由与节点判定不一致] → 共用同一函数。
- [与 `need_confirm` 顺序] → 无未定名称时分类已可能设确认；跳过反查后走 `route_after_remark_resolve` 等价逻辑即可，与现反查空返回后再路由一致。
- [字典再匹配在节点内] → 「正在爬」若分类未写 id，仍会进反查节点，节点内字典再匹配后可不打 HTTP；可接受（仍比全量空访少 thinking 误导更少；若需严格「字典再匹配后再决定是否进节点」，可把再匹配前移到路由，本变更不强制）。

## Migration Plan

- 仅改 feeding intent 图与反查节点导出；无 API 迁移。
- 回滚：恢复恒进反查边即可。

## Open Questions

- 无。

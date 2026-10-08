## Context

`resolve_remark_event` 在零命中时把 `fail_names` 交给 `_unrecognized_response`，用 `、` 拼接进「无法识别对应的事件「…」」。

`unresolved_event_slots` 同时收录：

1. 顶层 `event_name` 有名无 id  
2. `events[]` 中同条件子项  

分类后 `normalize_intent_events` 常把首项投影到顶层，于是同一专名出现两次；`resolved_cache` 只去重 HTTP，不减 `fail_names`。

## Goals / Non-Goals

**Goals:**

- 零命中文案与 `missing_events` 对同一专名只出现一次（保序）。
- 改动面最小，语义不变。

**Non-Goals:**

- 不改槽位收集策略（顶层 + events 双轨可保留）。
- 不做字典外语义猜确认；不改唯一/多命中路径。

## Decisions

### D1：在写入无法识别前对 `fail_names` 保序去重

在 `return _unrecognized_response(fail_names)` 前（或 `_unrecognized_response` 入口）用 `list(dict.fromkeys(fail_names))`（或等价）去重。

**替代**：改 `unresolved_event_slots` 跳过与 events 重复的顶层——治本但动路由判定面更大；本 change 仅修展示/名单。  
**替代**：仅文案去重、`missing_events` 不去——否决，二者应一致。

### D2：append 时也可防重

循环内 `if name not in fail_names: fail_names.append(name)` 与出口去重二选一或并用；出口去重即可满足规格。

## Risks / Trade-offs

- **[真多专名]** 「AD」与「DHA」仍应同时出现 → Mitigation：去重按字符串全等，不同名保留。  
- **[大小写变体]** 「AD」与「ad」视为不同 → 接受；与现匹配一致，不在本 change 归一化。

## Migration Plan

直接部署；无数据迁移。回滚即去掉去重一行。

## Open Questions

（无）

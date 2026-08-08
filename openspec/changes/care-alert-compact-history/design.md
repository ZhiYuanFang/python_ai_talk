## Context

care_alert 当前 `slim_history_events_for_prompt` + JSON，limit 40，拉取 last_7_days/80。产品要求缩短提示词：只今昨、紧凑行、独立名→id。

## Goals / Non-Goals

**Goals:** 今昨紧凑史 + 名 id 表；相对中文时间；拉取近两日。  
**Non-Goals:** 不改 tip/clinic 默认 JSON slim；不改全局通识 top_k（care_alert 与 clinic 同配置）；不做 7 日中位统计。

## Decisions

### D1: 两块注入

1. 流水：每行 `{相对start}{eventName}{后缀}`，无 id。  
2. 对照：`eventName=eventId` 去重；同名多 id 用 `|` 拼接或保留最近一条的 id（实现取**最近出现**的 id）。

### D2: 类型后缀

- `eventType/time` 或启发式有起止时长>0 → `{秒}秒`  
- `number` 或有 eventNumber → 数值  
- 否则 → `一次`

时长用原始 epoch 计算后再格式化 start 文案。

### D3: 窗口

- 注入：按上海日历过滤 today∪yesterday。  
- 拉取：`time_range=last_2_days`（昨 00:00 上海 → now），limit 适度（如 60）。

### D4: 通识与 clinic 同配置

- care_alert 不设 `knowledge_prompt_top_k` 覆盖；`search_vectors` 用全局 `settings.knowledge_prompt_top_k`（默认 1）。
- 提示词 `_compact_knowledge(limit=1)` 与检索上限一致。

## Risks / Trade-offs

- [无 eventId 的事件] → 对照表跳过该名；LLM 可能无法填 id，normalize 会丢无 eventId 项。  
- [同名多 id] → 保留最近一条 id。

## Migration Plan

仅 care_alert 路径；回滚恢复 JSON slim 即可。

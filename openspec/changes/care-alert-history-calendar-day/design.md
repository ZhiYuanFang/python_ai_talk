## Context

`care-alert-history-day-aggregate` 已将史行改为按日×事件聚合，但日标签仍为「今天/昨天」，且 `build_care_alert_history_prompt_blocks` 仍二次过滤今昨。用户消息已有 `逻辑日：YYYY-MM-DD`，拉取窗可能拉长；展示层应只按日历日标注并信任上游列表。

## Goals / Non-Goals

**Goals:**

- 日标签：同年 `MM-DD`，跨年 `YYYY-MM-DD`（相对逻辑日年，缺省上海 now 年）
- 去掉今昨过滤
- 多日按日期新→旧；同日按事件名
- 用户文案改为「近期记录」语义

**Non-Goals:**

- 不修改 `_care_alert_window` / `last_2_days`
- 不改总量分段、legend、无 id 史行
- 不编写测试

## Decisions

1. **锚点年**：`format`/`build` 增加可选 `anchor_date`（来自逻辑日）；未传则用 `now.date()`。跨年比较用 `event_date.year != anchor.year`。
2. **去掉** `_is_today_or_yesterday` / 「今天」「昨天」分支；无解析日则跳过该事件。
3. **分组键**：`(date, eventName)`；输出日标签由 `_format_day_label(d, anchor)` 生成。
4. **排序**：先按 `date` 降序，再按 `eventName` 升序。
5. **文案**：`care_alert_analyze` 中「近两日记录（今天/昨天；…）」→「近期记录（按日聚合：日期·时刻与总量；无 id）」；指令中「近两日」改为「近期记录」以免与多日窗矛盾。
6. **与 day-aggregate 并存**：本变更再 MODIFIED 同一 compact-history Requirement，收版时以后写全文为准。

## Risks / Trade-offs

- [拉取仍为 last_2_days 时行为几乎只变标签文案] → 可接受；为后续扩窗铺路。
- [列表极大时行数变多] → 仍由拉取窗限流，compact 不截断。

## Migration Plan

- 纯提示注入格式；回滚恢复今昨标签与过滤即可。

## Open Questions

- （无）

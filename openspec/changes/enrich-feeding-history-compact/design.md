## Context

`build_feeding_history_prompt_blocks` 已为多 Agent 共享。当前行格式为 `{日}·{名}·{时刻/…}·{总量}`，不含 remark；无本地摘要。调用方窗长不一（留意约 2 天、轨迹约 7 天），算法须对任意窗长同一套。

## Goals / Non-Goals

**Goals:**

- 备注绑在对应时刻上。
- 本地摘要：窗内全部日历日相邻链式、按 eventName 比增减，拼进 `history_text` 前缀。
- number 单位 = 事件 unit 字段；缺省 `ml`。
- 签名保持 `(history_text, legend)`。

**Non-Goals:**

- 不改 DataRequirement 窗长。
- 不用备注做对比键（对比键仅 eventName）。
- 不调用 LLM 做摘要；不写「异常/偏少」等诊断词。
- 不改 legend / care-alert eventId 契约。

## Decisions

### D1: 时刻挂备注

- 有非空 remark（trim）→ `08:10(AD)`；截断过长备注（建议 ≤12 字，超长加省略）。
- 进行中：`20:56~(夜醒)`（`~` 在备注括号前）。
- 无备注 → 保持原 `08:10` / `20:56~`。

### D2: 摘要拼进 history_text

```
【本地摘要】
{对比行…}
（空行）
{流水行…}
```

无任何可解析日数据时仍返回「（无）」；仅有流水无可比相邻对时，可只有流水或摘要注明无相邻日可比。

### D3: 窗内全部日历日链式对比

- 收集窗内出现过的上海日历日，升序；对每一对 `(D[i-1], D[i])` 生成一行（有非零 Δ 的事件才写入该行；整行无 Δ 则省略该行）。
- 文案：`{MM-DD或跨年ISO}较{前一日标签}：配方奶 +10ml；母乳 -10分钟`
- 逻辑日 `day` 仅作日标签跨年锚点（与流水一致），**不**截断对比链。

### D4: 按日按名计量

每个 `(日历日, eventName)`：

- count = 条数
- number：sum(eventNumber)，unit = 首个非空 unit，否则 `ml`
- time：sum(有效时长秒) → 摘要增减用分钟（四舍五入）
- one：只比 count

Δ：后日 − 前日；为 0 不报；仅一侧有数据的事件本对跳过（或可选报有无——本设计选跳过，只报双侧可算 Δ）。

### D5: 单位兜底

- 流水 `_format_number_sum` 与摘要共用：无 unit → `ml`（与「全缺兜底 ml」对齐；若流水当前空 unit 不写，本变更一并改为缺省 ml 以一致）。

## Risks / Trade-offs

- [7 天链式行多] → 仅输出有非零 Δ 的事件/日对。
- [intent daily 念摘要] → 接受（API 拼进 text 的取舍）；若过长可后续再拆第三返回值。
- [同名不同 unit] → 取首个非空；极端脏数据可能单位不稳。

## Migration Plan

1. 扩展 `format_feeding_history_group` 时刻备注。
2. 新增按日计量 + 链式摘要构建，拼进 `build_feeding_history_prompt_blocks` 的 history_text。
3. 手工：2 天/7 天窗各验一组；无备注/无昨日/unit 缺省 ml。

## Open Questions

- 无。

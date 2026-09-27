## Why

共享紧凑史已统一注入多 Agent，但流水不含备注，且缺少确定性「相邻日增减」摘要，模型需自行心算间隔与分事件变化，判断依据不稳。在 `feeding_history_compact` 内补备注挂载与本地日链式归纳，可一次改动惠及留意/轨迹/clinic/intent daily。

## What Changes

- 流水行时刻可挂备注：`HH:MM(备注)`；空备注不写括号；与进行中 `~` 可并存。
- 在 `history_text` **前缀**拼入本地摘要：对窗内**全部日历日**做相邻日链式对比（按 `eventName`），输出次数/总量/时长增减；**不**写诊断措辞。
- number 增减与流水总量的单位取事件 `eventUnit`/`unit`；全缺时兜底 `ml`。
- API 仍为 `(history_text, legend)`；摘要拼进 `history_text`，调用方无需改签名。
- 不改窗长、legend、Flutter eventId 契约、intent point 模板。

## Capabilities

### New Capabilities

- （无）

### Modified Capabilities

- `shared-feeding-history-compact`: 紧凑流水支持时刻备注；`history_text` 含窗内相邻日链式本地摘要；number 单位跟字段 unit（缺省 ml）。

## Impact

- 代码：主要 `app/shared/feeding_history_compact.py`；消费方继续读 `history_text` 即可（intent daily 也会念到摘要）。
- API：函数签名不变。
- Token：7 天窗摘要行变多；Δ≈0 可省略以控噪。

## Why

用户问「昨天喝了几次水」时分类已标 `history_mode=daily`，但 LLM 常把 `start_time`/`end_time` 留 0；规则预解析偏钟点，光「昨天」补不上整日窗。拉史无界变成多日【本地摘要】+ 毫升总量，听感不是「昨天几次」。即便窗对了，`number` 叶紧凑行只报「总量 xml」，不问次数。

## What Changes

- `history_mode=daily` 且 read 子项无有效时间窗时：按原文「今天/昨天/前天/本周」等**规则补整日（或约定区间）unix 窗**，再拉史；MUST NOT 在窗缺失时无界拉近期冒充「昨天」。
- 原文为次数问（几次/多少次等）时：daily 播报 MUST 显式给出次数（如「昨天喝水 1 次」或紧凑行带 `N次`）；`number` 叶 MUST NOT 仅用「总量 ml」回答次数问。
- 非次数问的 daily（吃了什么/和昨天比）可保留流水+总量/Δ 行为。
- 不改 Go；不关查史缓存飞轮。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `intent-history-query`: daily 缺窗须规则补日窗；次数问须报次数
- `shared-feeding-history-compact`: 次数问语境下 number 叶总量段或播报层须含次数（或由 speak 层拼句，设计选定一处）

## Impact

- **本仓**：分类后/确认前/speak 前补窗（`enum_to_unix` 或日词解析）、`speak_history` 与/或 `feeding_history_compact` 次数表达、可选与 `history_mode_cues` 共用「几次」线索。
- **关联**：衔接 `intent-history-mode-daily`、预解析钟点（本 change 补「整日」缺口）。

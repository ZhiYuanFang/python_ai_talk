## Context

日志复现：「昨天喝了几次水」→ daily + `start/end=0` → filter 无时间参数 → 多日紧凑块与 `总量10ml`。`enum_to_unix("yesterday")` 已存在；缺的是 daily 路径在窗为 0 时用日词填窗。次数问与 number 叶总量段语义错位。

## Goals / Non-Goals

**Goals:**

- daily + read 且窗无效时，按原文日词补上海日历窗后再拉史。
- 次数问 daily 播报用户能直接听到/看到次数。
- 有明确窗或 ignore 点查时不误伤。

**Non-Goals:**

- 本周/近 N 天的复杂自然语言全覆盖（可先支持今天/昨天/前天；本周可用 last_7 或另议）。
- 改 point 模板。
- 养育建议类问法。

## Decisions

### D1: 补窗时机 — 确认后执行前 / speak 拉史前

- **选择**：在 `speak_history`（及确认后 `_execute_after_confirm` 同一路径）拉史前：若 `history_mode=daily`、read 项 `ignore_time_range` 非真、且起止均无效，则从 `user_input`/pending 原文解析日词写入该 read 的 start/end。
- **备选**：仅靠 LLM/预解析 — 已失败，否决为唯一手段。
- 确认 pending 若已带上补后的窗更佳；至少 speak 前必须补，避免再无界拉取。

### D2: 日词映射复用 `enum_to_unix`

| 原文 | 枚举/行为 |
|------|-----------|
| 今天/今日 | today |
| 昨天/昨日 | yesterday |
| 前天 | 昨日起点再往前一日（实现可扩 enum 或本地算） |
| 本周/这周 | last_7_days 或「本周一 0 点～现在」（实现选一并注释） |

无日词但有「几次」且 daily：MAY 默认 today（须注释）；无强日词且无窗时 MUST NOT 静默拉全量却声称「昨天」。

### D3: 次数表达落在 speak 层

- **选择**：原文命中次数线索（与 `history_mode_cues`/classify 的几次词表对齐）时，`speak_history` 在 daily 紧凑块之上或替代为短句突出 **N 次**（按窗内该事件行数/组内 items 数）；number 叶可同时保留总量作辅，或紧凑行改为 `N次·总量xml`。
- **备选**：只改 compact 全局 — 会改「吃了什么」类观感，收窄到次数问更安全。

### D4: 与【本地摘要】Δ

- 次数问 + 单日窗：优先次数句；多日 Δ 摘要 MAY 省略或置后，避免盖过「几次」。
- 非次数 daily：保持现有流水+Δ。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 「和昨天比」被补成昨天单日窗 | 含「比/对比」时不要只取昨天；用更大窗或跳过默认 today |
| 补窗与 LLM 已填窗冲突 | 仅当起止均无效时补 |
| 进行中行计入次数 | 与 compact 同一 items 计数规则，注释说明 |

## Migration Plan

1. 纯本仓逻辑；旧缓存无窗 daily 命中后 speak 仍会补窗。
2. 回滚：去掉补窗与次数短句即可。

## Open Questions

（无；本周算法在实现时选一种写进注释即可。）

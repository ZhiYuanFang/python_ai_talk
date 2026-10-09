## Context

意图图入口 `match_intent_cache`：相似度与质量分达标即采用 payload、跳过 `classify_intent`。`rewrite_standalone_document` 对一切 `op=read` 写成「上一次{名}是什么时候」，导致几次类成功写入后文档与点查撞车；embedding 又对「喝水」等高权重，易误命中。产品要保留查史飞轮，不能整类禁用缓存。

## Goals / Non-Goals

**Goals:**

- 命中后、免确认执行前：查史类 payload 与本轮原文的 point/daily 线索冲突则拒命中。
- 写入时 daily/point 文档区分，避免全部改写成「上一次…」。
- 同问同 mode 仍跳过 LLM。

**Non-Goals:**

- 关闭查史缓存。
- 仅靠提高阈值阈值解决串台。
- 改 daily 播报为口语「N次」（另 change）。
- 清库迁移旧向量（门闩覆盖旧脏文档）。

## Decisions

### D1: 门闩在 match 接受路径，不取消飞轮

- **选择**：`match_intent_cache` 在分数/质量通过后，若 payload 含 read（或 target history），跑轻量线索校验；冲突 → `intent_cache_hit=False`，不写命中结果。
- **备选**：查史不缓存 — 违背飞轮，否决。

### D2: 线索规则对齐 classify 启发

| 原文强线索 | 期望 mode |
|------------|-----------|
| 几次/多少次/一共/总共/吃了什么/喝了多少/和昨天比/比昨天，或明显「今天/昨天/本周」+ 汇总语气 | daily |
| 上一次/上次/最近一次/什么时候（点查语气） | point |

- 仅当**能推断期望 mode** 且与 `payload.history_mode`（缺省当 point）冲突时拒命中。
- 两边都无强线索 → 不拦（保持现网宽松）。

### D3: 改写文档按 mode 分叉

- point / 缺省：保持「上一次{名}是什么时候」（备注变体保留）。
- daily：如「查询{名}今天或区间汇总」或带「几次」类独立句（实现选一句稳定模板即可），MUST NOT 再用「上一次…什么时候」。

### D4: 与 overlay 关系

- 门闩失败视为未命中，走既有 classify 边；不进入 `overlay_slots` 免确认。
- 门闩通过后 overlay 行为不变（时间窗覆盖仍可发生）。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 线索误伤（口语变体） | 只拦「有强线索且冲突」；模糊放行 |
| payload 无 history_mode 的旧条 | 缺省 point；几次类原文会拒命中 → 走 LLM 后写入带 mode 的新条 |
| 规则与 classify 漂移 | 共用或注释对齐同一词表 |

## Migration Plan

1. 部署后旧脏文档仍可被检索，但几次↔上一次冲突会被拒。
2. 回滚：去掉门闩与改写分叉即可。

## Open Questions

（无；「N次」播报不在本 change。）

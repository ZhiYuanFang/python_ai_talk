## Context

缓存命中后 `overlay_slots` 用 `extract_clocks_from_text` 覆盖 `start_time`/`end_time`，高置信可免确认落库。`execute_history_crud` 落库前再调 `apply_time_slots_to_events`，分类路径也会被规则盖时间。

现状：`_DAY_PERIOD_PREFIX` 只认「昨天/今日…」+「晚上/上午…」分立前缀，**不认「昨晚/昨夜」**。对「昨晚6点洗澡了」只匹配「6点」→ 今日 06:00，残留「昨晚」被丢弃，错误时间仍免确认执行。

多钟点降级（`should_degrade_multi_clock`，≥3）已存在，但管不了「单 clock + 未吃掉的日段」。

## Goals / Non-Goals

**Goals:**

- 「昨晚6点 / 昨夜6点」规则解析为昨日 18:00（Asia/Shanghai）。
- **半命中**：`len(clocks)≥1` 且原文去掉已匹配 span 后仍含未消费日/段时间词 → 取消缓存免确认，走 classify；落库前规则 MUST NOT 用该残缺 clock 覆盖。
- 与既有「≥3 钟点单条」降级并存、可叠加。

**Non-Goals:**

- 无 clock、仅「昨晚洗澡了」：本 change **不**强制降级（用户选定半命中策略）；可仍走缓存+现有默认「现在」。
- 不新增多段喂养拆条逻辑；不改 Go history API。
- 不在本 change 写测试文件。
- 不扩大为「任意残留词都降级」（仅时间日/段类残留）。

## Decisions

### D1: 先补词法，再加半命中兜底

- **选择**：`_DAY_PERIOD_PREFIX`（或等价）增加复合前缀「昨晚|昨夜」，语义 = `day_offset=-1` + 晚上段（1–11 → +12）。
- **备选**：只靠 LLM 兜底、不补词法 → 常见说法每次打 LLM，贵且慢。
- **理由**：主路径修对；兜底只挡未知说法（如「前晚」「昨儿晚上」若未入库）。

### D2: 半命中判定 = 有 clock ∧ 有未消费时间残留

- **选择**：用已匹配 `ClockHint.raw` 的 span 从原文挖空后，对残留跑「日/段时间词」探测（含：昨天/今日/前天、昨晚/昨夜、早上/晚上/上午…、今早/今晚 等未进完整 clock 前缀的词）。
- **触发**：`len(clocks) ≥ 1` 且残留命中 → 半命中。
- **不触发**：无 clock（纵有「昨晚」）→ 本条不降级；有 clock 且残留无时间词 → 正常覆盖。
- **备选**：任意残留即降级 → 「6点洗澡了」挖空后仍有「洗澡」会误伤。故必须限定时间词表。

### D3: 共用判定，双路径一致

- **选择**：在 `closed_interval`（或 extractor 旁）提供例如 `has_unconsumed_temporal_residual(text, clocks)` / `should_degrade_partial_clock(...)`。
  - `overlay_slots`：半命中 → 同多钟点降级：`intent_cache_hit=False`，进 classify。
  - `apply_time_slots_to_events`：半命中 → **跳过 clock 时间写入**（时长/数量仍可按现有规则；或整段时间跳过、数量保留——推荐跳过 clock/闭合时间写入，避免错误 start）。
- **理由**：分类后 LLM 已填时间时，落库前再 `apply` 会用「今日6点」踩掉「昨日18点」。

### D4: 与多钟点降级的关系

- 半命中与 `len(clocks)≥3` 独立 OR：任一为真则降级/跳过残缺覆盖。
- 「8点到8点半」两 clock 且无残留 → 不半命中、不按多钟点降级（闭合 change 语义保持）。

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| 时间残留词表不全 → 仍有漏网半命中 | 词表覆盖探索中已知口语；漏网可再扩词；主路径已修「昨晚」 |
| 词表过宽 → 误降级（如「点」字） | 仅匹配完整日/段词，不单字「点」 |
| 挖空 span 重叠/顺序错误 | 按 match 区间从后往前删除或用占位符 |
| LLM 分类仍解错时间 | 属分类质量；本 change 只保证不「假正确」免确认落库 |
| 免确认变确认 → 多一次交互 | 可接受；错误落库成本更高 |

## Migration Plan

1. 部署后无需数据迁移。
2. 回滚：还原 extractor / degrade 判定即可。
3. 验收：「昨晚6点洗澡了」→ 昨日 18:00；故意构造未入库日段+clock → 走 LLM 非免确认错误落库。

## Open Questions

- （已决）降级策略：仅当抽到 clock 且仍有残留。
- 「今早 / 今晚」是否纳入词法前缀：建议本 change 一并纳入残留词表；若实现成本低可同时进前缀合法解析（可选增强，不阻塞半命中）。

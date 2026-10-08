## 1. 钟点词法：昨晚 / 昨夜

- [x] 1.1 在 `time_slot_extractor` 为复合日段「昨晚」「昨夜」增加前缀解析（日偏移 −1 + 晚上段 1–11→+12），中文注释说明语义
- [x] 1.2 确认「昨晚6点」「昨夜6:30」等与既有「昨天晚上」路径不互相吞匹配（重叠时保留更完整 span）

## 2. 半命中判定

- [x] 2.1 实现「挖空已匹配 clock span 后探测未消费日/段时间词」的共用函数（建议落在 `closed_interval` 或 extractor 旁），词表覆盖 design 所列日/段词
- [x] 2.2 实现 `should_degrade_partial_clock`（或等价）：仅当 `len(clocks)≥1` 且存在时间残留时为真

## 3. 覆盖与落库接入

- [x] 3.1 `overlay_slots`：半命中时与多钟点降级相同，取消 `intent_cache_hit` 并进入分类路径
- [x] 3.2 `apply_time_slots_to_events`：半命中时 MUST NOT 用残缺 clock 写入 start/end（避免踩掉 LLM 时间）；数量规则可按现有逻辑保留
- [x] 3.3 确认与 `should_degrade_multi_clock`（≥3）为 OR 关系，双钟点起止无残留时不误伤

## 4. 手工验收

- [x] 4.1 「昨晚6点洗澡了」→ 昨日 18:00，非今日 06:00
- [x] 4.2 构造「未入库日段词 + 钟点」半命中 → 不走免确认错误落库，进入 LLM 分类
- [x] 4.3 「昨晚洗澡了」（无钟点）→ 不因本规则单独取消缓存命中

## 1. 分类提示与字段

- [x] 1.1 在 `INTENT_CLASSIFICATION_SYSTEM_TEMPLATE` 增加顶层 `history_mode`（point|daily）及选用规则；JSON 示例带上该字段
- [x] 1.2 写明：上次类 → point + ignore_time_range=true；区段次数/合计/清单/事实对比 → daily + 窗 + ignore=false
- [x] 1.3 写明：养育建议与「最近怎么样」→ conversation + 简洁引导 clinic；禁止装懂查史
- [x] 1.4 确认 classify 解析/`IntentResult` 保留 `history_mode` 与 `limit` 并透传到 speak_history

## 2. 播报与 limit

- [x] 2.1 `speak_history`：确认 `history_mode=daily` 走紧凑聚合；point 不变
- [x] 2.2 daily 且 limit 为空时默认提高拉取条数（≥50），中文注释说明
- [x] 2.3 （可选）分类后启发：有窗且文案含几次/一共等且未写 mode → 纠偏为 daily

## 3. 手工验收

- [x] 3.1 「今天喂了几次…」→ daily 播报，非仅「上一次」
- [x] 3.2 「上次换尿布什么时候」→ point
- [x] 3.3 「最近怎么样」→ conversation 引导 clinic，不查史装建议
- [x] 3.4 「够不够吃」→ conversation 引导 clinic

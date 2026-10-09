## 1. 预解析与提示注入

- [x] 1.1 实现短格式预解析组装（clocks raw/unix/可选可读时间、duration_sec、partial），复用现有 extractor / residual 判定
- [x] 1.2 `build_intent_classification_system_prompt` 支持注入时间预解析块到 `{extra}`（紧接进行中计时）
- [x] 1.3 `classify_intent` 在调 LLM 前计算预解析并传入 builder

## 2. 瘦提示

- [x] 2.1 压缩 `INTENT_CLASSIFICATION_SYSTEM_TEMPLATE` 中自行换算日段/时长→unix 的长文；保留开表/闭合/ignore/多事件等必要字段约束
- [x] 2.2 增加：非 partial 预解析优先采用 unix；reasoning 禁止逐步推算 Unix（须中文）

## 3. 确认前规则盖时间

- [x] 3.1 在 `postprocess_feeding_result`（或等价）创建 leaf_confirm / 多事件确认前，对 CUD `events[]` 调用 `apply_time_slots_to_events`
- [x] 3.2 用盖写后的 start/end 传入确认话术构建；半命中跳过残缺覆盖（沿用 closed_interval 行为）
- [x] 3.3 确认多事件与单事件路径均走盖写后再生成问句

## 4. 手工验收

- [x] 4.1 「昨晚6点…」分类提示含预解析；确认话术为昨日晚间而非今日早上
- [x] 4.2 抽检 reasoning 无明显逐步推 Unix 长链（相对改前）
- [x] 4.3 半命中用例确认前不被残缺 6 点盖成今日早上

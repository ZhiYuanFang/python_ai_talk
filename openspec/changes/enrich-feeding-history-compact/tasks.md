## 1. 时刻备注

- [x] 1.1 在组行格式化中读取 remark，非空则绑到对应时刻 token；支持与 `~` 并存；过长截断
- [x] 1.2 确认空备注不输出括号；史行仍无 eventId

## 2. 本地日链式摘要

- [x] 2.1 按上海日历日 × eventName 计量（次数；number 求和+unit；time 时长秒）
- [x] 2.2 对窗内全部日历日升序相邻对生成增减文案；Δ=0 省略；双侧缺一侧跳过
- [x] 2.3 number 单位取字段 unit，全缺兜底 `ml`；与流水总量口径一致
- [x] 2.4 将「【本地摘要】…」拼到 `history_text` 流水之前；无数据仍「（无）」；legend 不变

## 3. 校验

- [x] 3.1 全仓确认仍仅通过 `build_feeding_history_prompt_blocks` 消费形态（签名未破）
- [x] 3.2 `openspec validate enrich-feeding-history-compact --strict` 通过

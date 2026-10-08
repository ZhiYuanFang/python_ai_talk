## 1. 槽位口语格式化

- [x] 1.1 在 `clarification`（或 `feeding/utils`）实现 `format_confirm_slot`：反推日段/相对日、120s「现在」阈值、区间/开表/结束/瞬时+量模式；中文注释完整
- [x] 1.2 改写 `build_leaf_confirm_message`：接受事件槽位（或 event dict），外壳「您是要{片段}吗？」；无槽时走「现在」
- [x] 1.3 改写 `build_multi_event_confirm_message`：逐项调用 `format_confirm_slot`，保留「并」/顿号拼接

## 2. 管道传槽

- [x] 2.1 `intent_pipeline` 叶子 `create_leaf_confirm_pending`：传入 head/events[0] 的 start_time、end_time、quantity（及 op/action 所需字段）
- [x] 2.2 确认显式 `confirm_message` 覆盖仍优先；查/删路径不改话术函数

## 3. 手工验收

- [x] 3.1 无时间开始睡觉 → 含「现在开始」
- [x] 3.2 无时间记录洗澡 → 含「现在记录」
- [x] 3.3 带 start+quantity 配方奶 → 含反推日段/钟点与毫升
- [x] 3.4 闭合睡眠区间 → 含起止
- [x] 3.5 多事件确认各项时间/量可见；查记录确认句式未误伤

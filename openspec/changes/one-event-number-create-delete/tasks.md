## 1. 落库数量

- [x] 1.1 在 `collect_event_items` 中，叶子 `type` 或 `event_type` 为 `one` 且子操作为新增或删除时，`eventNumber` 设为 1
- [x] 1.2 `number` 仍用解析数量；`time`（含动作名为 `one` 的补记）和修改保持现有赋值

## 2. 手工确认

- [ ] 2.1 记一笔「拉了屎」类 `one` 事件，batch 的 `eventNumber` 为 1
- [ ] 2.2 删除该 `one` 事件时 `eventNumber` 为 1；「吃了120配方奶」仍为 120

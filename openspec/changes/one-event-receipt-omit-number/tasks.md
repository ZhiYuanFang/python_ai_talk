## 1. 回执

- [x] 1.1 `collect_event_items` 把叶子类型写入 `_leaf_type`（认 `type` 与 `event_type`），不进入 Go 请求体
- [x] 1.2 `render_persist_content` 在 `_leaf_type` 为 `one` 时，新增和修改回执不拼接 `eventNumber`；计量事件仍带数量和单位

## 2. 手工验收

- [ ] 2.1 说「尿尿了」成功后回执为「已记录尿尿。」，不再出现 1
- [ ] 2.2 记录配方奶 120 仍回执带 120 和单位

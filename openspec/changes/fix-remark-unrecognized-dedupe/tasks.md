## 1. 零命中专名去重

- [x] 1.1 在 `resolve_remark_event` 零命中路径：对 `fail_names` 保序去重后再调用 `_unrecognized_response`（或在 `_unrecognized_response` 入口统一去重）；中文注释说明顶层与 `events[]` 镜像导致重复
- [x] 1.2 确认 `missing_events` 与用户可见「无法识别…」文案使用同一去重列表；不同专名仍全部保留
- [x] 1.3 手工核对：单专名双槽 →「AD」一次；两专名 → 两项均在

## Context

`collect_event_items` 在叶子类型为 `one` 且操作是新增或删除时，把 `eventNumber` 写成 1。`render_persist_content` 看到非 0 的 `eventNumber` 就拼进回执：「已记录{名} {数量}{单位}」。尿尿没有单位，于是变成「已记录尿尿 1」。

`execute_batch` 会丢掉以下划线开头的字段，那些字段不会发给 Go。

## Goals / Non-Goals

**Goals:**

- `one` 的新增、修改成功回执只说事件名。
- 计量事件的回执仍带数量和单位。
- 发给 Go 的 `eventNumber` 不变。

**Non-Goals:**

- 不改点查、日汇总里怎么说条数。
- 不改删除回执。
- 不把 `eventNumber` 改回 0。

## Decisions

1. **类型留在本地字段。** `collect_event_items` 把已经算好的叶子类型写入 `_leaf_type`（`type` 或 `event_type`，小写）。`execute_batch` 现有规则会剥掉它。

2. **回执按类型跳过数量。** `render_persist_content` 在 `_leaf_type == one` 时，新增和修改都不拼 `qty_txt`。没有这个字段的旧条目仍按现在的数量规则，避免漏报计量事件。

## Risks / Trade-offs

- [字典没写类型时仍会念出 1] → 与现在强制写 1 的条件相同，类型缺失就不算 one。

## Migration Plan

- 只改 `history_crud.py`。
- 回滚去掉 `_leaf_type` 和回执判断即可。

## Open Questions

- （无）

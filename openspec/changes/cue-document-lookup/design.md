## Context

各飞轮 `list_entries` 会 `collection.get` 全量后再按 offset 切片，且没有 document 条件。Hub 若对 9 个列表逐页过滤，既重复全量读取，又会被单页 500 条上限漏掉后面的命中。

## Goals / Non-Goals

**Goals:**

- 一个 HTTP 接口按 trim 后的原文精确返回九个集合的命中。
- 命中带维度键，供 Go 选择对应的删除接口。

**Non-Goals:**

- 语义检索、模糊包含、类型向量、规则工单。
- 在本接口里删除向量。

## Decisions

### D1：聚合路由，各 store 自过滤

- **选择**：`GET /v1/admin/cues/by-document`。每个 store 提供按 document 精确过滤的方法，内部仍一次 `get`，但只把命中返回给聚合层。聚合层串行或有界并发调用这九个方法。
- **理由**：避免 Go 分页把同一集合 get 很多次。
- **备选**：Chroma `where_document` → 各版本算子不一致，精确相等用取回后比较更稳。

### D2：维度键固定

- **选择**：返回 `dimension` 为 `op`、`intent`、`qty`、`time`、`remark`、`read_source`、`predict`、`history_speak`、`locate`，并带 `collection` 名与 `id`、`document`、`payload`。
- **理由**：与 Go 现有 `/voice/admin/api/*-vectors/{id}` 一一对应。

### D3：空串与失败

- **选择**：trim 后为空返回 400。任一 store 失败则 500，不返回部分命中。
- **理由**：部分成功会被当成「这句没灌进那个维度」。

## Risks / Trade-offs

- [九个集合各一次全量 get] → 与现在打开一个维度列表的代价同级，只在运维查询时发生。

## Migration Plan

先部署本接口，再发 Go Hub。旧列表接口不变。

## Open Questions

- （无）

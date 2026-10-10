## Why

运维 Hub 意图向量列表当前按 Chroma `get()` 原始顺序分页，条序与写入时间无关，难以及时看到最近灌种/覆盖的条目。需要管理列表按时间**新→旧**稳定排序后再分页。

## What Changes

- **Python** `list_entries` / `GET /v1/admin/intent-cache`：全量取出后按 `created_at` **降序**（新→旧）排序，再应用 `offset`/`limit`。
- 同分或缺失时间时用稳定次序（如 id 字典序）；空/`""` 的 `created_at` MUST 排在有时间戳的条目之后。
- **不改** 运行时匹配、dedupe 保留规则、bulk/delete 语义；Go Hub 透传列表即可（表格跟 API 顺序，无需前端再排）。

## Capabilities

### New Capabilities

- （无）

### Modified Capabilities

- `intent-vector-admin-api`：管理列表 MUST 按 `created_at` 新→旧排序后再分页。

## Impact

- **python_ai_talk**：`app/feeding/services/intent_cache_store.py`（`list_entries`）；路由可仅补注释
- **go_ai_talk**：通常无需改代码（代理透传）；Hub 序号仍为 `offset + 行序`
- 无 MySQL；无运行时匹配门槛变更

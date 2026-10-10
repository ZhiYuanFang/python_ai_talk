## 1. Store 列表排序

- [x] 1.1 `list_entries`：全量组装条目后按 `created_at` 降序、空时间沉底、同分 id 升序排序，再 `offset`/`limit` 切片
- [x] 1.2 补中文注释：说明新→旧、空 `created_at` 与平局规则；注明 `created_at` 为最近写入时间

## 2. 路由与校验

- [x] 2.1 `GET /admin/intent-cache` 文档/注释写明响应 `items` 为按时间新→旧
- [x] 2.2 `openspec validate intent-cache-list-newest-first --strict` 并修规格问题

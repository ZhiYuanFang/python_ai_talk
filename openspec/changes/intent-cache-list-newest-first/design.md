## Context

管理列表 `IntentCacheStore.list_entries` 对 Chroma `collection.get()` 结果按索引直接切片，顺序不稳定且与时间无关。metadata 已有 `created_at`（ISO 字符串；`add`/`update` 写入时均为 `datetime.now().isoformat()`，故语义接近「最近写入时间」）。Hub 经 Go 代理透传 Python `GET /v1/admin/intent-cache`，表格序号为 `offset + 行序`。

## Goals / Non-Goals

**Goals:**

- 列表在分页前按 `created_at` **新→旧**排序
- 分页边界与排序一致（先排后切）
- 空时间戳与同分有稳定次序

**Non-Goals:**

- 不改 dedupe 保留规则（仍质量高 / 早 `created_at`）
- 不改 bulk/delete、运行时匹配
- 不新增 sort query 参数、不做前端二次排序
- 不回填历史空 `created_at`、不引入持久「首次创建」字段

## Decisions

1. **排序落点：Python store**  
   在 `list_entries` 内全量排序再 `offset`/`limit`。Go/Hub 只展示响应顺序，避免前端排导致跨页错乱。

2. **键：`created_at` 字符串降序**  
   现有值均为 ISO-8601 可比较；降序即新→旧。不引入额外 DB 索引（Chroma 无富查询）。

3. **空 `created_at` 沉底**  
   缺失或 `""` 排在所有有时间戳条目之后（新→旧浏览时先看到可解释时间的行）。同为空时再比 id。

4. **平局：id 升序**  
   与 dedupe 稳序习惯一致，保证同页刷新不抖序。

5. **规格形态：ADDED**  
   基线尚未合并「列表排序」条款；本 change 对 `intent-vector-admin-api` 增加「列表按时间新→旧」Requirement，不改动其他管理接口条款。

## Risks / Trade-offs

- [全量 get 再排序] → 与现列表路径一致；条目量级仍适合内存排序，过大再议游标/索引。
- [`created_at` 在 update 时刷新] → 列表「新」含刚覆盖的旧文案；与产品「看最近写入」一致，文档中注明即可。
- [与未收版的 `intent-cache-admin-dedupe` 并存] → 无冲突；序号仍跟分页后顺序，排序后序号 1 对应最新一条（首页）。

## Migration Plan

- 部署 Python 即可生效；无需数据迁移。
- 回滚：恢复旧 `list_entries`（按 get 原序切片）。

## Open Questions

- （无；方向已定为新→旧）

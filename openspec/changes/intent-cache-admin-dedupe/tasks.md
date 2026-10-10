## 1. Python Store：判重与整理

- [x] 1.1 `intent_cache_store`：抽出 document 规范化键（`strip`），与 `_find_id_by_document` 一致
- [x] 1.2 实现 `dedupe_exact_documents`：按键分组，保留 quality_score 高 / created_at 早 / id 稳序一条，删除其余；返回 kept/deleted
- [x] 1.3 改 `bulk_upsert`：库中已有或本批已见同键则跳过（不调用 update）；累计 `added` / `skipped` / `failed` / `ids`

## 2. Python Admin 路由

- [x] 2.1 `POST /admin/intent-cache/dedupe` 调 store，返回 deleted 列表
- [x] 2.2 `POST /admin/intent-cache/bulk` 透出 `added`/`skipped`（保留 `ok`/`failed`/`ids` 兼容）
- [x] 2.3 路由与 store 方法补中文业务注释

## 3. Go 代理（兄弟仓 go_ai_talk）

- [x] 3.1 `PythonAIClient`：`IntentCacheBulkResult` 增加 `Added`/`Skipped`；新增 `DedupeIntentCache` → `POST /v1/admin/intent-cache/dedupe`
- [x] 3.2 `api/v1/voice_intent_vectors_http.go`：bulk 响应字段；新增 `POST .../intent-vectors/dedupe` 请求/响应类型
- [x] 3.3 `voice_admin_intent_vectors.go`：Bulk 透传 added/skipped；实现 Dedupe 控制器方法

## 4. Go Hub 页面

- [x] 4.1 `intent-vector-admin.html`：表头/行第一列序号（`offset+i+1`）
- [x] 4.2 「整理重复」按钮：调 dedupe，弹窗展示 deleted（id+document），无则提示无重复，完成后刷新
- [x] 4.3 bulk 提交后弹窗：新增数 + 跳过 document 列表；摘要可同步写 `mainMsg`

## 5. 校验

- [x] 5.1 `openspec validate intent-cache-admin-dedupe --strict` 并修规格问题

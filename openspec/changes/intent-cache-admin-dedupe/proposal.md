## Why

Hub 意图向量管理页需要看清条数、清理「同一句话多条」脏数据，并在批量灌种时拒绝文案完全相同的重复写入。当前 Python `bulk` 走 `add`（同 document 覆盖），Hub 列表无序号、无整理入口、bulk 结果也不区分跳过；需本仓 API 与兄弟仓 Go Hub **同一变更内一起改**。

## What Changes

- **重复定义（A）**：`document` 去首尾空白后字符串完全相等即视为重复（不比 payload、不比相似度）。
- **Python**：新增 `POST /v1/admin/intent-cache/dedupe`；管理 `bulk` 对已有同 document **跳过**（不覆盖）；响应带 `added` / `skipped` / `deleted`。
- **Go Hub**：`intent-vector-admin.html` 列表第一列加序号；「整理重复」按钮 + 删除结果弹窗；bulk 提交后弹窗展示新增与跳过。
- **Go 代理**：`PythonAIClient` + voice admin API 透传 dedupe，bulk 响应增加 `added`/`skipped`。
- **保留** 运行时确认后 `add` 的「同 document 更新」；不做模糊去重。

## Capabilities

### New Capabilities

- `intent-vector-admin-hub`：运维 Hub 意图向量页的序号列、整理重复与 bulk 结果展示（实现于兄弟仓 `go_ai_talk`）。

### Modified Capabilities

- `intent-vector-admin-api`：整理重复接口与 bulk「跳过相同 document」及响应字段。

## Impact

- **python_ai_talk**：`intent_cache_store.py`、`intent_cache_admin.py`
- **go_ai_talk**：`python_ai_client.go`、`voice_intent_vectors_http.go`、`voice_admin_intent_vectors.go`、`resource/public/intent-vector-admin.html`
- 无 MySQL；无运行时匹配门槛变更

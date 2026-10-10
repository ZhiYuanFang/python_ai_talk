## Context

Python 已有 `/v1/admin/intent-cache` list/bulk/delete；`bulk_upsert` 调 `add` 会覆盖同 document。Go voice-service 经 `PythonAIClient` 反代为 `/voice/admin/api/intent-vectors*`，页面 `intent-vector-admin.html`。产品要双仓一起落地：判重 A、整理、bulk 跳过、列表序号与弹窗。

## Goals / Non-Goals

**Goals:**

- Python：bulk 跳过同 document；dedupe 每组留 1；稳定 JSON 供 Hub。
- Go：代理 dedupe；bulk 透传 skipped/added；Hub 序号列 + 两处结果弹窗。
- 重复 = `document.strip()` 全等。

**Non-Goals:**

- 不改运行时 `add` 覆盖语义。
- 不做近义/模糊去重。
- 不改 Admin 鉴权模型（仍 X-Admin-Password）。

## Decisions

1. **判重键** — `document.strip()`，与 `_find_id_by_document` 一致。

2. **bulk 跳过** — 库中已有或本批已见同键 → `skipped`，不 `update`。响应：`{ ok, added, skipped:[{index,document,existing_id?}], failed, ids }`（`ok`≈`added`）。

3. **dedupe 保留** — 同键多条：高 `quality_score` → 早 `created_at` → 小 id。  
   Python：`POST /v1/admin/intent-cache/dedupe` → `{ kept, deleted:[{id,document,quality_score}], groups }`。  
   Go：`POST /voice/admin/api/intent-vectors/dedupe` 原样透传。

4. **Hub UI**  
   - 表头第一列 `#`；行号 = `offset + i + 1`（当前页 offset=0 即 1…n；`listMeta` 仍显示 total）。  
   - 「整理重复」→ 调 dedupe → `alert`/`dialog` 列 deleted（id + document），无删除则提示无重复；完成后刷新列表。  
   - bulk 成功后弹窗：新增 N、跳过列表（document）；一行摘要也可留在 `mainMsg`。

5. **双仓落地顺序** — 先 Python API，再 Go client/API/HTML；Hub 可短暂忽略未知字段，但本变更一次提交两侧。

6. **OpenSpec 归属** — 规格与 tasks 写在本仓 change；实现时改 `../go_ai_talk` 对应文件（与 `intent-last-time-slots-hub` 同模式）。Go 仓可不另开 change，除非对方仓库要求。

## Risks / Trade-offs

- [Risk] 只部署一侧 → Mitigation：tasks 要求两侧同批完成；Hub 弹窗兼容空 skipped。
- [Risk] 保留策略删「较新覆盖条」→ Mitigation：优先 quality；可先看列表。
- [Risk] 弹窗用 `alert` 简陋 → Mitigation：本版可用 `alert`/`confirm` 拼文本，不引入新 UI 库。

## Migration Plan

- 先发 Python，再发 Go（或同窗口部署）。
- 回滚：Python 恢复 bulk=add、下线 dedupe；Go 去掉按钮与字段透传。

## Open Questions

-（无）

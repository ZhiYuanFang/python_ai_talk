## Why

TYPE 维仍用本地弱规则（如句内含「睡」即 create）短路，未覆盖的问句（如「睡了多久了」）进不了 TYPE LLM，误记睡眠。规则缺口箱又把 type/event/shape/time/quantity 全部灌进 Hub，噪音大、无法当作「扩 TIME/QTY 规则」工单。TYPE/SHAPE 应改为与 EVENT 同构的**按维关键字飞轮**：冷路径 LLM（可自报是否确认）+ `keywords[]` 落库，热路径命中跳过 LLM；Hub 可整理类型向量；缺口箱只保留 TIME/QTY。

## What Changes

- **BREAKING（TYPE 判定）**：去掉 TYPE 维「喂养口语线索 → 默认 create」等假覆盖短路；SHAPE 并入 TYPE（不再独立 SHAPE 小 LLM / shape 缺口）。
- TYPE：**先查类型关键字向量库** → 命中则填 `target_type`/`op`/`history_mode` 并跳过 TYPE LLM；未命中则 TYPE 小 LLM 一次产出类型结果 + `need_confirm` + `keywords[]`。
- 冷路径：`need_confirm=false`（高置信）直接采用并按 `keywords[]` 写入类型库；`need_confirm=true` 则用户确认后再写入。
- TIME/QTY：**保留规则**，规则未命中再 LLM；仅此类「规则未覆盖且 LLM 抓到」写入规则缺口。
- **BREAKING（缺口箱）**：停止 `rule_gap` 写入 `type` / `shape` / `event`；Hub/API 展示与列表默认仅 `time`|`quantity`。
- 新增类型向量管理 API（镜像事件短说法 admin：list/bulk/dedupe/delete），供 Go Hub 整理类型缓存；独立 Chroma 集合，不与 `feeding_intents` 混存。

## Capabilities

### New Capabilities

- `intent-type-keyword-flywheel`：TYPE（含原 SHAPE）关键字向量飞轮——匹配、LLM 契约（含 need_confirm/keywords）、写入时机
- `intent-type-vector-admin-api`：类型向量库管理 HTTP（list/bulk/dedupe/delete），供 Hub 整理

### Modified Capabilities

- `intent-segment-multidim`：TYPE 维改为飞轮优先；SHAPE 不再单独成维
- `intent-dim-llm-fallback`：TYPE LLM 契约扩展；去掉独立 SHAPE 兜底要求（并入 TYPE）
- `intent-shape-llm-fallback`：形态裁定并入 TYPE；废止独立 SHAPE LLM/缺口
- `intent-rule-gap-inbox`：缺口仅 TIME/QTY；禁止 type/shape/event 灌箱
- `feeding-intent-user-confirmation`：TYPE 冷路径仅当 LLM 声明 need_confirm 时确认；高置信不强制 leaf_confirm

## Impact

- **Python**：`segment_multidim` TYPE 路径、`segment_dim_llm` / `SEGMENT_TYPE_LLM_PROMPT`、新类型向量 store、停写 type/shape/event 缺口、`rule_gaps_admin` 过滤、新 `/admin/type-cache`（或等价）路由。
- **Go Hub（兄弟仓）**：类型向量整理页（对标 intent-vectors）；规则缺口页只展示 TIME/QTY。
- **体验**：「睡了多久了」冷路径走 TYPE LLM→history；热路径关键字命中加速。

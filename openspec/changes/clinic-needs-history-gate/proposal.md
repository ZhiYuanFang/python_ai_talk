## Why

Clinic 数据准备在判断「拉哪些事件、多长时间」之前，没有先判断「回答是否需要喂养历史」。闲聊与纯知识题仍会走 scope LLM + Go history API；thinking 文案已是「要不要翻记录」，实现却永远当需要。应拆出独立门禁节点，按需再做范围判断与拉取。

## What Changes

- 新增共享节点 `judge_needs_history`：宽松判断是否需要喂养历史；LLM/解析失败默认 `needs_history=true`
- 保留 `judge_data_requirement` 仅负责 event_ids / time_range / limit（不扩 `needs_history` 字段）
- `clinic_graph` 与 clinic 流式 `prepare_steps`：`judge_needs_history` →（条件）→ `judge_data_requirement` → `fetch_history`；不需要时跳过后两步并置 `history_events=[]`
- 上游强制：intent `history`、tip 路径跳过门禁（或 `force_needs_history=true`），直接进入范围判断或既有硬编码拉取
- 门禁只影响喂养历史；`search_vectors` / `fetch_baby_profile` 行为不变
- 更新 clinic thinking 文案，使「要不要 / 翻多久 / 正在翻」与三节点一一对应

## Capabilities

### New Capabilities

- `needs-history-gate`: 在拉取喂养历史前先判断是否需要；条件跳过范围判断与拉取；失败默认需要；上游可强制需要

### Modified Capabilities

- （无主库 `openspec/specs/` 基线；行为变更由本 change 的新 capability spec 覆盖）

## Impact

- 共享节点：`app/shared/graphs/nodes/`（新 `judge_needs_history` + prompts；`clinic_graph` / clinic 路由步进；可选 `fetch_history` 防御性短路）
- 状态：`ClinicState`（及经 clinic 图的 intent 路径）增加 `needs_history` / `force_needs_history`
- 上游：`call_clinic_agent`（history 强制）、tip 流式（不接入门禁，保持硬编码 `data_requirement`）
- tip_graph：可不挂门禁节点（入口仍为范围判断或直拉）
- 对外 HTTP API 契约不变；多一次布尔 LLM（需要历史时共两次判断 LLM）

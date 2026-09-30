## Why

意图智能体当前有三类体验问题：点查「上次」把进行中事件的开始时间当成上一次；意图缓存命中后整包复用 payload，用户说的钟点/毫升被丢掉；冷启动依赖缓存但缺少运营侧灌种子与纠错入口；一句话多次喂养（同叶多时刻）亦未写成正式验收场景。本期打包修复上述行为，并提供仅打 Chroma 的 Hub 管理能力；**不**引入 MySQL 双写（LoRA 导出留待后续）。

## What Changes

- **点查「上次」语义**：跳过进行中记录，优先答上一笔已完成；若仅有进行中一条，回「目前仅找到一条记录，是xx点发生，正在进行中」。
- **缓存命中后槽位覆盖**：规则从本轮原文抽取 clock / quantity，盖到缓存 `events[]` 后再免确认执行；多钟点且种子仅一条时**一律强制走 LLM**（取消本次缓存免确认）。
- **同叶多时刻 create**：正式 Scenario——一句含多个钟点与毫升可拆成多条 `create`（允许同一 `event_id` 多次），确认文案须带时间与数量；Go batch 一次提交。
- **Hub 意图向量管理**（跨仓）：Go 管理页入口 + voice-service 代理；Python 提供 list / bulk upsert / delete；权威存储仍为 `feeding_intents`（Chroma）。
- **明确不做**：MySQL `intent_seeds` / `intent_training`、Python→Go 静默写库、训练表 `device_no`。

## Capabilities

### New Capabilities

- `intent-slot-overlay`: 意图缓存命中后的 clock/qty 槽位覆盖与多钟点降级策略
- `intent-vector-admin-api`: Python 侧意图向量管理 API（列表、批量写入、按 id 删除）；供 Go Hub 调用

### Modified Capabilities

- `intent-history-query`: 「上次」选行跳过进行中；仅进行中时的固定话术
- `intent-analysis`: create 可填 `start_time`；同叶多时刻多条 `events[]`
- `feeding-intent-user-confirmation`: 多事件确认文案须含各条时间与数量（若有）
- `langgraph-intent-graph`: 缓存命中后增加 `overlay_slots`（或等价）节点后再路由
- `intent-cache-flywheel`: 写入/种子骨架不宜冻结绝对 `start_time`；与槽位覆盖配合

## Impact

- **本仓**：`speak_history` 选行与模板；`match_intent_cache` 之后槽位覆盖；`quantity_extractor` / 新建 clock 抽取；classify system 提示；多事件确认文案；`intent_cache_store` list/bulk/delete；新 admin HTTP 路由。
- **兄弟仓 go_ai_talk**：gateway Hub 模块与静态页；voice-service admin API 代理 Python；扩展 `PythonAIClient`。无新 MySQL 表。
- **兼容**：免确认仍仅限缓存高置信路径；LLM 分类路径仍默认确认。不恢复 tip / 外置 prompt 飞轮。

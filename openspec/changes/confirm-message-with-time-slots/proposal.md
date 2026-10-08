## Why

喂养确认话术常只说「您是要记录「洗澡」吗？」，用户无法核对将落库的钟点、区间与数量。多事件虽已带粗粒度「（今天 HH:MM）」，单事件基本不带时间，且管道常未把 `start_time`/`end_time` 传入 pending。需要按**实际将落库的时间戳**反推口语日段，无时间则明确说「现在」。

## What Changes

- 统一确认槽位口语：由 `op`/`action`、`event_name`、`quantity`、`start_time`、`end_time` 生成片段（开表 / 单点 / 单点+量 / 区间）；日段从 Asia/Shanghai unix **反推**，不回放用户原话。
- **无有效时间**（空/0/不可解析）时，create/start/end 类确认 MUST 带「现在」（如「现在开始「睡觉」」「现在记录「洗澡」」）。
- 单事件 `build_leaf_confirm_message` 与多事件 `build_multi_event_confirm_message` 共用同一格式化逻辑；`intent_pipeline` 叶子确认传入子项时间与数量。
- **不改**：查记录 / 删除确认话术（本 change 仅覆盖记录类 create/start/end）。
- **不改**：SSE 事件类型；禁止新增测试文件。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `feeding-intent-user-confirmation`：记录类确认 MUST 在可知时带出口语时间（反推日段）与数量；无时间 MUST 使用「现在」；区间 MUST 读出起止；多事件继续逐项拼接。

## Impact

- 代码：`app/feeding/services/clarification.py`（话术）、`app/feeding/services/intent_pipeline.py`（传槽位）；可选小工具函数同文件或 `feeding/utils`。
- API：仍为 `confirm_message` 字符串；文案更丰富，契约字段不变。
- Go/前端：播报更长句，无需改协议。

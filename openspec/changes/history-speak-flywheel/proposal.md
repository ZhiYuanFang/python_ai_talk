## Why

点查硬编码「优先最近已完成」使「睡了多久了」在存在进行中睡眠时仍答上一笔完整睡眠用时。选行策略与进行中播报口径应由句意决定，不能写死；且不宜继续塞进 TYPE 飞轮。

## What Changes

- 新增**独立**查史播报飞轮集合（如 `feeding_history_speak_cues`）与小 LLM：两维 **`point_pick`**（`latest`|`prefer_completed`）与 **`open_speak`**（`elapsed`|`in_progress`）。
- **BREAKING（点查选行/话术）**：`speak_history` 点查不再无条件优先已完成；按上述两维选行与拼句。缺维或非法 MUST 调小 LLM，**禁止**静默默认 `prefer_completed`。
- 热路径：关键字命中且两维合法 → 跳过 LLM；冷路径 LLM 出两维 + `keywords[]`（直播，默认不因策略维强制确认）。
- Admin API（对标 type-cache）供 Hub 整理；不写 `rule_gap`。
- daily / predict 不进本飞轮；TYPE 仍只负责 `history`+`point`。

## Capabilities

### New Capabilities

- `intent-history-speak-flywheel`：独立查史播报飞轮、两维契约、缺维走 LLM、点查落地与 admin

### Modified Capabilities

- `intent-history-query`：废止无条件「优先已完成」；选行/进行中话术服从 `point_pick` / `open_speak`

## Impact

- 代码：`speak_history`、新 store、`prompts/system.py` 新常量、段/意图组装透传两维、admin 路由
- 兄弟仓 Go Hub：查史播报向量整理页（tasks 标明兄弟仓）
- 与 `type-keyword-flywheel` / `intent-predict-dual-channel` / `predict-active-timing-eta` 分轨：TYPE/predict/ETA 逻辑保留；`open_speak=in_progress` 时可继续拼 ETA

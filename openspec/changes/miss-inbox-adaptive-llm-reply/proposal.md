## Why

终局 miss 时用户收到固定硬文案（无法识别 / 估不准 / 暂不支持等），体验生硬；设备上往往已有预测算法快照与宝宝画像，却未用于话术。需要在**不改变 miss 统计与「答不出」主定位**的前提下，用可选缓存与画像让 LLM 生成更自然的对外回复。

## What Changes

- 在判定并落库覆盖缺口之后，对外 `content` 可经 LLM 自适应润色（中文 reasoning / SSE 透出约定不变）。
- 润色提示可注入：用户原话、规范失败语义（硬模板 / `fail_kind`）、**若存在且未过期**的 `predict_algo` 设备快照（无则不注入、不重算）、宝宝基础信息（有则给、无则跳过）。
- **MUST NOT** 因润色改变：`infer_miss_fail_kind` 判定、inbox 写入时机与条数、确认中不记、插话 barge 的 miss 语义（须基于规范 `fail_kind` / 硬信号，而非软文案关键词）。
- inbox 记录的 `reply` 仍存规范硬模板（或等价规范失败文案），便于运营对照缺口；用户侧只见软回复。
- 「数据量太少，无法预测」仍不并入 miss 清单（与既有约定一致）；本 change 不改该门控。

## Capabilities

### New Capabilities

- `agent-miss-adaptive-reply`: 终局 miss 对外话术的按需 LLM 润色；可选预测快照与宝宝画像注入；与 miss 统计解耦。

### Modified Capabilities

- （无基线独立 capability 名；行为增量挂在新 capability。既有 miss inbox 落库语义保持，见 change `time-dayword-flywheel-miss-inbox` 产物。）

## Impact

- `app/api/routes/intent.py` 的 `_finish_intent_response`（或等价统一出口）
- `app/feeding/services/agent_miss_record.py` / barge 判定：判定顺序与 `fail_kind` 稳定
- 只读 `predict_algo_cache`、`http_client.get_baby_profile`；新 system 提示词常量
- 不改 Go miss 契约字段形状（仍返回 IntentResponse.content）

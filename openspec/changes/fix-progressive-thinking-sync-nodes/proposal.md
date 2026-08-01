## Why

Intent 流式路径改用 `progressive_thinking` 手写步进后，对节点一律 `await node_fn(state)`。`match_event_by_vector` 是同步函数并直接返回 `dict`，触发 `TypeError: object dict can't be used in 'await' expression`，`/intent/stream` ASGI 崩溃。需立即修复，使步进助手兼容 sync/async 节点（与 LangGraph 行为对齐）。

## What Changes

- `run_one_step_with_thinking` / `run_linear_steps_with_thinking`：调用节点时若返回 awaitable 再 await，否则将返回值视为 patch dict（兼容同步节点）。
- 不强制把 `match_event_by_vector` 改成 async（可选后续优化）；本 change 以辅助层兼容为主。
- 无 API **BREAKING** 变更。

## Capabilities

### New Capabilities

- `progressive-thinking-node-compat`: 流式步进助手对 sync/async 图节点均可安全执行并合并 state

### Modified Capabilities

- （无主库基线；本 change 以新 capability 描述回归修复要求）

## Impact

- **代码**：`app/shared/progressive_thinking.py`；consumers：`intent.py`（首发）、clinic/tip 线性步进（已多为 async，行为不变）
- **API**：恢复 `/v1/analyze/intent/stream` 冷启动可跑通 match 节点

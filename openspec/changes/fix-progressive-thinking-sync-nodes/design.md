## Context

`progressive_thinking` 在 yield thinking 后执行 `await node_fn(state)`。Intent 图入口 `match_event_by_vector` 为同步 def，调用后立即得到 `dict`，`await` 崩溃。LangGraph `astream` 曾兼容 sync；手写步进未保留该语义。

## Goals / Non-Goals

**Goals:**

- 步进助手对 sync 与 async 节点均可执行并 `state.update(patch)`
- 修复 `/intent/stream` 在 match 步的 TypeError
- 保持「先 thinking 再执行」顺序不变

**Non-Goals:**

- 不把向量检索改成真正的 async IO（可另开）
- 不改节点业务逻辑与路由分支
- 不回退到 astream 驱动字幕

## Decisions

### 1. 在辅助层统一调用，而非改节点签名

- **选择**：抽 `_invoke_node(node_fn, state)`：调用后若 `inspect.isawaitable(result)` 则 await，否则当作 patch
- **理由**：一处修复覆盖 linear + one-step；不强迫改 `match_event_by_vector`（仍被 graph ainvoke 使用）
- **备选**：仅改 match 为 async → 只修一个节点，其它 sync 仍隐患

### 2. 不在线程池跑 sync（本 change）

- **选择**：同步节点仍在事件循环线程直接跑（与改前 LangGraph 默认同风险）
- **理由**：最小修复；`to_thread` 属性能后续

## Risks / Trade-offs

- [sync 节点阻塞事件循环] → 与历史行为一致；后续可 to_thread
- [节点返回非 dict 非 awaitable] → 现逻辑仅 update dict；保持不变

## Migration Plan

1. 部署后打 `/intent/stream`，确认 thinking 后进入 match 无 TypeError
2. 回滚：恢复盲目 await（不推荐）

## Open Questions

- 无

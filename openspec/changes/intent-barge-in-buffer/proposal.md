## Why

用户在意图思考过程中常继续说话：闲聊插话会打断或并行开第二轮图，且首句未必是目标句。需要按设备单飞跑图、插话入缓冲，本轮终局后再决定丢弃或拼接重跑，避免错听与重复思考。

## What Changes

- Python 按 **deviceNo** 维护意图插话缓冲 + busy 单飞：同 device 同时仅一轮意图图在跑。
- 设备已 busy 时再次调用意图 API：请求 **挂起**，文本入缓冲；不启第二张图；本轮（含可能的 miss 拼接重跑）结束后再返回。
- **占坑连接**负责完整 SSE（thinking + 终答，含服务端内起重跑）；挂起连接结束后返回同一终答快照或「已合并」轻量响应，**不**重放思考气泡。
- 本轮结束判定：
  - **agent_miss 清单命中**（与 `infer_miss_fail_kind` 严格一致）→ 本轮原文与缓冲 **全量拼接** → **立刻清缓冲** → 重跑意图（最多 **5** 轮）。
  - 能回答 / 确认消歧 / 非 miss 降级（含「数据量太少，无法预测」）→ **丢弃缓冲**，直接出答或进确认。
  - 确认中插话一律丢缓冲。
- 清空时机：思考正常结束、开始重跑、过程异常；另设缓冲 **TTL 10 分钟** 自动过期。
- 「数据量太少，无法预测」**不**并入 agent_miss，不触发拼接重跑。

## Capabilities

### New Capabilities

- `intent-barge-in-buffer`：按 device 单飞、插话缓冲、miss 拼接重跑、挂起二次请求与缓冲生命周期

### Modified Capabilities

- （无基线独立 capability 树名时以本 change spec 为准；意图流式入口行为变更写入本 capability。）

## Impact

- 本仓：`/v1/analyze/intent` 与 `/intent/stream` 入口闸门、device 缓冲存储（建议 Redis，TTL 600s）、与 `agent_miss_record.infer_miss_fail_kind` 对齐的重跑触发、最多 5 轮内起重跑
- 客户端：需容忍同 device 并发 POST 挂起；以占坑连接 SSE 为准展示思考
- 不改预测算法本身；与 `predict-local-fallback-llm` 分 change
- 不写测试文件

## Context

意图分析一次请求一句 `text`，SSE 推思考与 answer。用户思考中再说话时，现网易并行第二轮或客户端取消首轮。已有 `infer_miss_fail_kind` / agent_miss 定义终局失败。Python 已用 Redis（闸门、companion、预测算法快照），可复用客户端做 device 级缓冲与 busy。

## Goals / Non-Goals

**Goals:**

- 同 deviceNo 同时仅一轮意图图；插话入缓冲。
- busy 二次 POST 挂起至本轮（含 miss 重跑）结束。
- miss（严格 agent_miss）→ 全量拼接 → 清缓冲 → 重跑 ≤5。
- 结束 / 重跑启动 / 异常必清缓冲；TTL 10min。
- 确认中丢缓冲；「数据量太少，无法预测」不触发 miss 重跑。

**Non-Goals:**

- 改 Flutter 默认取消 SSE 策略以外的产品文案（客户端适配挂起即可）。
- 把预测「数据量太少」并进 miss。
- 跨 device 合并会话；按 conversation_id 分匣（本版按 deviceNo）。

## Decisions

### D1：Busy + 缓冲（deviceNo）

- Redis（或等价）键：`intent_barge:{deviceNo}`，载荷含 `busy`、`anchor_text`（占坑原文）、`pending[]`（插话）、`rerun_count`、可选 `waiter` 协调。
- TTL：**600s**（与探索一致，防死锁）。
- 空闲 POST：设 busy、anchor=text、开跑。
- busy POST：append pending，**await** 本轮完成事件，再返回。

### D2：挂起响应形态

- **占坑请求**：唯一完整 SSE（thinking + answer；服务端内 miss 重跑仍在此连接推送，可继续 thinking）。
- **挂起请求**：不跑图、不推 thinking；本轮全部结束后返回与占坑相同的终答快照，或明确「已合并处理」轻量 JSON/SSE answer-only。
- **MUST NOT** 让挂起连接再开一套思考泡，避免双 UI。

**Alternatives：** 短 ack 202——否决（产品要求挂起跟重跑）。挂起也完整重放 SSE——否决（重复与成本）。

### D3：Miss 触发与拼接

- 触发：`infer_miss_fail_kind(...)` 非空（且非 need_confirm / options）。
- **不**因「数据量太少，无法预测」触发（该文案不改正 miss 清单）。
- 拼接：`anchor_text + pending` 按时间序空白连接（实现可定分隔符为空格或换行，须稳定）。
- 拼接后 **立刻清 pending**（及按规则重置/保留 busy 至重跑结束），然后用拼句重跑；`rerun_count += 1`，上限 **5**；达上限则终局出最后一次结果并清匣。

### D4：清空

| 事件 | 清缓冲 |
|------|--------|
| 能答 / 确认态结束 | 是，释放 busy |
| miss 拼接后、重跑启动前 | 是（pending）；busy 保持到重跑结束 |
| 重跑启动 | 再清 pending（幂等） |
| 异常 | 是，释放 busy |
| TTL 到期 | 是 |

确认中（need_confirm / options / confirm_type）：丢弃 pending，不拼接。

### D5：入口挂钩

在 `analyze_intent` / `analyze_intent_stream`（及确认续跑若共用 device）最前做 busy 闸门；图结束后统一 `finalize_barge`（判 miss → 拼接重跑循环或释放）。

## Risks / Trade-offs

- [挂起连接占 worker/超时] → 超时与 TTL 对齐或略长；文档告知客户端。
- [多端同 device 互串] → 按产品接受（一宝一跑）；否则二期加 conversation_id。
- [达 5 轮仍 miss] → 终局返回，清匣。
- [「数据太少」不重跑] → 用户补事件名若只触发该文案不会拼句；可接受（探索已拍）。

## Migration Plan

1. 落地缓冲 store + 意图路由闸门与 finalize。
2. 客户端验证：并发两 POST，仅一条思考流。
3. 回滚：关掉闸门即恢复并行多图。

## Open Questions

（无；挂起跟重跑、miss 清单、数据太少不并入、≤5、TTL 10min 已敲定。）

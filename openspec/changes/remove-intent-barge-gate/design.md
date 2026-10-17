## Context

意图同步与流式入口在跑图前调用 `intent_barge_store.begin_or_enqueue`。同设备已有 `busy` 且 `status=running` 时，新请求成为挂起方，只把原话写入 `pending` 并等待终局，不进入意图图。占坑方仅在 `finish_success` / `finish_error` 时关匣。流被取消不会走进 `except Exception`，匣保持 `running`。挂起方每次 `_save` 都把键的 TTL 重新设为 600 秒，所以设备会一直被挡在图外。

覆盖缺口且缓冲非空时，占坑方还会把锚点与后续句拼起来重跑，最多 5 次。

## Goals / Non-Goals

**Goals:**

- 每次 `/v1/analyze/intent` 与 `/v1/analyze/intent/stream` 都用本句直接跑意图图。
- 去掉设备级占坑、挂起、拼接重跑，以及对应 Redis 读写。
- 卡住的 `intent_barge:{device_no}` 不再影响后续请求。

**Non-Goals:**

- 不改成「新句抢占并取消旧思考」。旧请求继续跑完自己的图。
- 不改确认续聊、十分钟对话、漏答自由回答。
- 不在启动时扫描并删除已有闸门键。

## Decisions

### D1：入口不再咨询闸门

同步与流式都删掉 `begin_or_enqueue`、`wait_for_final`、`maybe_prepare_concat_rerun`、`finish_success`、`finish_error`。请求文本直接进入现有冷启动或 `conversation_id` 续聊。

备选是给匣加代次，让新句取消旧句。用户要求删除新旧句闸门，而不是改成抢占。

### D2：删除闸门模块

`app/feeding/services/intent_barge.py` 与 `intent_barge_store.py` 仅被意图路由使用。路由去掉引用后删除这两个文件，避免再写 `intent_barge:` 键。

### D3：已有键自然过期

代码不再读取该键。残留键靠原有 TTL 消失。不增加清理任务。

### D4：同设备并行可同时落库

两句同时进来会各开一张图，都可能写喂养记录。这是去掉单飞之后的结果，不另加锁。

## Risks / Trade-offs

- [两句同时落库互相覆盖] → 接受。本变更不再把它们串成一句。
- [覆盖缺口不再拼接插话重跑] → 接受。每句只按自己的原话回答。
- [旧进程仍在跑、新进程已删闸门] → 旧进程写的键不会被新进程读取，新请求仍能进图。

## Migration Plan

发布后新请求直接进图。无需迁移数据。回滚是恢复闸门调用与两个模块。

## Open Questions

无。

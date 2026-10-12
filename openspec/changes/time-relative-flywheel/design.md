## Context

TIME 维现状：规则（clock / apply_time_slots）→ TIME LLM（出 Unix）→ rule_gap；规格明确禁时间飞轮。原因是绝对 Unix 跨天复用会错一天。探索拍板 **纯 A**：只缓存相对配方，命中时用当前 Asia/Shanghai 物化；不做同日绝对 TTL。本 change 独立于 `fix-read-route-qty-remark-flywheel`。

约束：中文注释；禁止测试文件；feeding 内改；保留 rule_gap。

## Goals / Non-Goals

**Goals:**

- `feeding_time_cues`：document=段整句；payload=相对配方；禁止 Unix 主缓存。
- 判定序：规则 → 飞轮(配方→物化) → TIME LLM(主出配方) → 合法配方才回写；仍写 time rule_gap。
- LLM 仅有 unix、无合法配方：当次可落库，不写飞轮。
- read 轨跳过；`resolve_time` 对齐 `dim_resolve` 形状。
- 改写「时间禁飞轮」相关 Requirement。

**Non-Goals:**

- 同日绝对 Unix TTL（方案 B）。
- unix→配方反推一期不做。
- 完整日历/星期/农历；枚举先收紧。
- Hub 前端（可选兄弟仓）；Go 变更。

## Decisions

### D1：纯相对配方，禁绝对主缓存

```json
{
  "kind": "instant" | "interval" | "duration_to_now" | "open_start",
  "points": [
    {
      "day": "today" | "yesterday" | "day_before",
      "period": null | "morning" | "noon" | "afternoon" | "evening" | "night",
      "hour": 0-23,
      "minute": 0-59
    }
  ],
  "duration_minutes": null
}
```

- `instant`：1 point，物化后 end=start  
- `interval`：2 points  
- `duration_to_now`：`duration_minutes` + end=now  
- `open_start`：1 point，end=0  

校验失败或物化失败 → 当 miss。

**Alternatives：** 同日 TTL 绝对 unix — 用户否决。反推 unix→配方 — 一期不做。

### D2：判定序与接线

```
① extract / apply_time_slots 规则成功 → 用规则（可不写飞轮）
② time_cue 命中合法配方 → materialize(now) → unix
③ TIME LLM（注入当前 Shanghai）主出配方；可附带当次 unix
④ 配方合法 → 整段回写；无论是否回写，规则 miss 且调了 LLM → rule_gap
⑤ 仅 unix 无配方 → 当次落库，不写飞轮
```

调用方：`segment_multidim` 的 TIME 段；封装 `resolve_time`。

### D3：LLM 契约

改 `SEGMENT_TIME_LLM_PROMPT` / `llm_resolve_time`：JSON 以 `formula`（或等价字段）为主；`resolved=false` 则无结果。服务端校验配方后再物化；附带 unix 仅作当次便利，**回写只认配方**。

### D4：范围门闩

- `target_type=read`：不读不写 TIME 飞轮（与备注/数量一致）。
- create/update（含补记、开表）可读可写。

### D5：Admin

`/v1/admin/time-cache`：list / bulk / delete；bulk 校验配方字段，拒绝仅含 unix 的条目。

## Risks / Trade-offs

- [模型仍只吐 unix] → 不写飞轮，热路径暂不加速；靠提示与人工种子  
- [枚举过窄] → 未覆盖口语冷路径 + rule_gap 扩规则/后续扩枚举  
- [物化与规则边界不一致] → 规则优先；飞轮仅规则 miss 后  
- [旧「禁飞轮」spec 冲突] → 本 change REMOVED/ADDED 收口  

## Migration Plan

1. 发版：store + materialize + resolve_time + 提示词 + admin。  
2. 可选种子：常见整句相对口语（昨晚八点等）。  
3. 金线：冷写配方 → 次日同句无 TIME LLM 且物化为新的「昨晚」。  
4. 回滚：停读 time_cue，恢复「规则→LLM→gap」。

## Open Questions

（无：纯 A 与禁 TTL / 禁反推已拍板。）

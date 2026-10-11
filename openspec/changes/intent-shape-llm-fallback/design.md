## Context

`resolve_shape` 在 `op=end` 时给 `action=end`，否则 `type=time`+`create` 固定 `start`。TYPE 的 `_END_RE` 仅覆盖「结束|停了|…」，「睡醒了」被「睡」线索打成 create → 开表。EVENT LLM 已能定「睡眠」。需在 SHAPE 补规则词 + 小 LLM，与 `intent-dim-llm-fallback` 其它维风格一致。

## Goals / Non-Goals

**Goals:**

- time 叶正确区分开始 / 结束 / 补记闭合。
- 「睡醒了」→ 结束睡眠；「睡着了/睡觉了」→ 开始（或不误判为 end）。
- 窄契约 SHAPE LLM + `rule_gap(llm_used=true)`。

**Non-Goals:**

- 改 EVENT 匹配或明细备注。
- 满血 classify。
- 为 one/number 叶常规路径强制打 SHAPE LLM。

## Decisions

### D1：管道

```
规则结束线索（扩表）→ op=end, action=end
否则 type!=time → 原推导（one 等）
否则 type=time && create：
  若段含开/关暧昧或结束态口语未进词表 → SHAPE 小 LLM
  否则默认 start（与现网一致）
```

**Alternatives：** 凡 time 叶一律 LLM——可作后续加严；首版偏触发保守以控延迟。

### D2：规则词扩写（先于 LLM）

在 TYPE 或 SHAPE 共用结束线索：`醒了|睡醒|起床|醒过来|睡完` 等 → `op=end`。  
开始线索（可选，防误伤）：不强行；「睡着了」不含「醒」即可免 end。

### D3：SHAPE LLM 契约

输入：段原文、`event_name`、`event_type`、当前规则倾向的 op/action。  
输出：`{ "op": "create|end", "action": "start|end|one" }`。  
约束：睡着/开始睡 → create+start；睡醒/醒了/结束 → end+end；有起止时长补记 → create+one。禁止改事件。失败则保留规则结果。

### D4：回写

LLM 返回 `op=end` 时 MUST 同步 `draft.op` 与 `draft.action`，以便确认话术与 batch 走结束路径。

### D5：模块

- `SEGMENT_SHAPE_LLM_PROMPT` in `prompts/system.py`
- `llm_resolve_shape` in `segment_dim_llm.py`
- `resolve_shape` 改为 async 或由 `resolve_segment` 在推导后按需调用

## Risks / Trade-offs

- [睡着误判 end] → 提示对比睡着 vs 睡醒；规则「醒」优先于「睡」子串  
- [延迟] → 仅 time 叶 + 触发条件  
- [与 TYPE 双写结束词] → 抽共享 `_END_CUES` 常量避免分叉  

## Migration Plan

1. 扩结束线索 + SHAPE LLM 挂接。  
2. 验收：睡醒了→结束；睡着了→开始；结束睡眠→end。  

## Open Questions

- 是否对所有 time+create 一律 LLM：默认否，先词表+暧昧触发。

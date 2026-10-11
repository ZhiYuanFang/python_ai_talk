## Context

`intent-segment-multidim` D2 约定 TYPE / EVENT / TIME / QTY 规则 miss 后小 LLM 兜底；实现仅规则 + `rule_gap`。`intent-remark-extra-names` 补了 EVENT 的 extra_names / Go 反查与明细备注 LLM，但 Go 零命中即「无法识别」，仍无事件小 LLM。用户「睡着了」暴露该缺口。约束：禁止满血 classify；SSE `stream(thinking_enabled=True)`；中文 reasoning；提示词在 `prompts/system.py`。

## Goals / Non-Goals

**Goals:**

- 四维窄契约小 LLM：TYPE、EVENT、TIME、QTY。
- EVENT：在 Go 反查之后、失败重说之前插入小 LLM；口语可对齐表内叶。
- 兜底调用写入 `rule_gap` 且 `llm_used=true`。
- 与备注明细 LLM、分句 LLM 并存，职责不混。

**Non-Goals:**

- 恢复满血一次多 events 分类。
- SHAPE 维 LLM。
- TYPE/TIME/QTY 向量飞轮。
- Hub 新页（沿用缺口 admin）。

## Decisions

### D1：管道位置

```
TYPE:  规则 →〔TYPE 小 LLM〕
EVENT: 词典 → extra_names → 向量 → Go 反查 →〔EVENT 小 LLM〕→ 失败重说
REMARK明细: 事件已定后（已有，本 change 不改契约）
SHAPE: 推导
QTY:   规则 →〔QTY 小 LLM〕→ number 缺量仍追问
TIME:  规则 → 半命中弃权 →〔TIME 小 LLM〕
```

**Alternatives：** 并回满血 classify——否决。仅补 EVENT——否决（用户要求对齐设计补齐各维）。

### D2：各维触发与契约

| 维 | 触发 | 输出 JSON（示意） | 硬约束 |
|----|------|-------------------|--------|
| TYPE | 无句级 type 且规则无线索/冲突 | `target_type`, 可选 `op`/`history_mode` | 枚举内；不确定可 feeding+create |
| EVENT | 阶梯至 Go 后仍无唯一 `event_id` | `event_id`,`event_name` 可空 | 只能选自注入叶子表；禁止编造；专名无把握必须空 |
| TIME | 有时间线索但半命中或有词无可用 unix | `start_time`,`end_time` 或标明无法解析 | 半命中须先丢弃残缺规则时间再调 |
| QTY | 段内像有量但规则抽空 | `quantity` 或 null | 完全无量线索 → 不调 LLM，number 叶走追问 |

### D3：EVENT 与「禁止常识升格」

小 LLM 做**表内对齐**（睡着→睡觉），不是备注升格（AD→营养品）。提示词明确：短英文/补剂名等专名若表内无直接对应且无把握 → 空 id。Go 反查已给证据的路径不会进本步。

### D4：模块与提示

- 新建 `segment_dim_llm.py`（或等价）：四函数 + 共用 `stream_llm_collect`。
- 四常量：`SEGMENT_TYPE_LLM_PROMPT`、`SEGMENT_EVENT_LLM_PROMPT`、`SEGMENT_TIME_LLM_PROMPT`、`SEGMENT_QTY_LLM_PROMPT`。
- EVENT 注入：叶子 `event_id`/`event_name` 短表（可截断超长表，优先常用/全表视体量）。

### D5：缺口与飞轮

- 凡调用维级兜底：`rule_gap_store.record(..., llm_used=True, llm_result=摘要)`。
- EVENT LLM 命中且用户确认后：仍按既有短说法飞轮写段原文→事件（与 phrase 规格一致）。

### D6：单事件语义

规格文案从「单事件零 LLM」改为：**跳过分句与满血 classify**；维级小 LLM 与明细备注 LLM 按需允许。

## Risks / Trade-offs

- [延迟] → 仅 miss 触发；提示极短  
- [EVENT 误升格 AD] → 提示禁升格 + 空 id 优先于猜类别  
- [TIME 幻觉 unix] → 半命中先弃权；LLM 失败保持 0  
- [字典表过长] → 截断/分组注入；日志记录  
- [与 remark change 并行] → 明确 EVENT 插在 Go 之后  

## Migration Plan

1. 实现四维 helper 并挂入 `resolve_segment`。  
2. 联调：睡着了→睡觉；昨晚6点半命中走 TIME LLM；AD 无史→空→无法识别/重说。  
3. 无需清库；phrase 随确认增长。

## Open Questions

- EVENT 注入全表 vs Top-N：默认全叶子，表过大再截断。  
- TYPE LLM 与默认 create：无线索时调 LLM 还是直接 create+gap；**默认先调 LLM 一次**。

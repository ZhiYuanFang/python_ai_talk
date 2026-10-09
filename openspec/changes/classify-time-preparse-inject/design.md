## Context

冷路径：`in_progress_probe` → `classify_intent`（LLM 填 start/end，提示含大段日段/时长换算）→ `postprocess` 建 leaf_confirm（用 LLM 时间反推话术）→ 用户确认后 `execute_history_crud` 再 `apply_time_slots`。规则时间能力已在 overlay/落库使用，分类未享。用户感知的「时间慢」主要来自 classify 的时间推理与冗长时间条文，而非 `overlay_slots` CPU。

产品已定：**C + 瘦提示**——软注入预解析；确认前规则盖时间；压缩手算提示。

## Goals / Non-Goals

**Goals:**

- 分类前短块注入 clocks/duration/partial，减少 LLM 推 Unix。
- 瘦身 system 中自行换算时间的长说明；明确 reasoning 勿逐步推 Unix。
- 建确认 pending 前对 CUD events 跑 `apply_time_slots_to_events`，确认话术与落库一致。

**Non-Goals:**

- 不改缓存命中 overlay 主流程。
- 不关闭 SSE `thinking_enabled`。
- 不做硬约束「JSON 必须等于预解析」（软提示即可；权威在确认前规则）。
- 不写测试文件；不扩按需探针（可另 change）。

## Decisions

### D1: 策略 C — 软注入 + 确认前规则权威

- **选择**：hint 写「优先参考预解析 unix」；`postprocess_feeding_result`（或等价、建 leaf_confirm 之前）对 `events[]` 调用 `apply_time_slots_to_events(user_input, events)`，用结果写回 fields 再确认。
- **备选**：硬锁 JSON（B）→ 半命中难处理；仅注入不盖确认前 → 确认与落库仍可能不一致。
- **理由**：与 execute 同规则；加速靠少推理 + 瘦提示，正确性靠规则。

### D2: 预解析内容与挂点

- **选择**：`extract_clocks_from_text` + `extract_duration_seconds` + `should_degrade_partial_clock`（或等价 residual 标记）；格式短文本/迷你 JSON（raw、unix、可选上海可读时间、duration_sec、partial）。
- 注入：`build_intent_classification_system_prompt` 的 `extra`（进行中摘要之后）。
- 调用：`classify_intent` 构建 prompt 前计算，传入 builder。

### D3: 瘦提示原则

- **保留**：字段含义（start/end、开表 end=0、闭合 end>start）、ignore_time_range、多事件各带时间、计量冲突条款（既有）。
- **压缩**：教模型自己做「昨晚→昨日18点」「无钟点10分钟→now−10m」的逐步换算长句；改为指向预解析块 +「无预解析时用简规则 / 可留 0 由服务端规则补」。
- **加**：reasoning 须中文；**禁止逐步推算 Unix**；有预解析非 partial 时优先抄 unix。

### D4: partial / 无钟点

- partial：extra 标明「规则半命中，勿采用残缺单点」；确认前 apply 已跳过残缺 clock。
- 无 clocks：extra 写「无规则钟点」；不强迫填假 unix。

### D5: 多事件确认

- 确认前 apply 盖完再 `build_multi_event_confirm_message` / `create_leaf_confirm_pending`，保证多段时间话术一致。

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| extra 过长抵消瘦提示 | 限制为短列表，无缩进大表 |
| 模型仍长篇推时间 | 条文禁止 + 瘦手算；抽检 reasoning |
| 确认前 apply 盖掉 LLM 刻意时间 | 与落库一致是目标；partial 不盖残缺 |
| 读 history 的时间窗被误盖 | apply 主要改 create 时间；读窗若被影响则仅对 CUD create/update 子项应用或保持现 apply 语义并验收 |

## Migration Plan

1. 部署即可，无数据迁移。
2. 回滚：去掉注入、恢复提示长文、去掉确认前 apply。

## Open Questions

- （已决）C + 瘦提示；缓存不管；不关 thinking。
- execute 是否跳过二次 apply：可选幂等保留，不阻塞本 change。

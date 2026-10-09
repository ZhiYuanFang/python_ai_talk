## Context

`speak_history` 已支持 `history_mode=daily` → `build_feeding_history_prompt_blocks`（日×事件紧凑行 + 相邻日链式增减前缀）。分类默认不写该字段，代码回落 `point`，故「今天几次」仍像「上一次」。产品边界：事实查史（含次数/合计/事实 Δ）归 intent；养育建议与「最近怎么样」归 clinic。

## Goals / Non-Goals

**Goals:**

- 分类可稳定产出 `history_mode=point|daily` 并驱动播报。
- 提示分流：点查 / 区段汇总 / 建议拒识（「最近怎么样」→ clinic 侧）。
- daily 区段提高 limit 可配置或提示默认值，减少截断。

**Non-Goals:**

- intent 图内 HTTP 调 clinic。
- 改写 daily 紧凑格式或 point 模板语义。
- 改删非 latest 定位；新建字典外事件类型。

## Decisions

### D1: 顶层 `history_mode`，非 per-event

- **选择**：与现 `IntentResult.history_mode` 一致，整次 history 读共用一个 mode。
- **备选**：每 read 子项自带 mode → 改动更大，本 change 不需要。
- 多 read 子项时：若任一条需要汇总语义，分类应整单 `daily`（或拆成两次交互——提示要求单次意图统一 mode）。

### D2: 分流表（写入提示）

| 用户语义 | target | history_mode | ignore_time_range | 备注 |
|----------|--------|--------------|-------------------|------|
| 上次/上一次/最近一次 | history | point | true | 可填窗但服务端忽略 |
| 今天/昨天/本周 + 几次/一共/清单/和昨天比 | history | daily | false | 必填 unix 窗 |
| 够不够、怎么办、正常吗、**最近怎么样** | conversation | — | — | content 引导去喂养建议/clinic；不编造分析 |

### D3: conversation 引导文案

- **选择**：分类 `content` 简洁固定语义，如「养育建议请使用喂养建议功能」类短句（中文）；不假装已查史。
- 上游若已按 intent 结果路由 clinic，仍可识别 conversation + 关键词；本 change 不依赖图内调 clinic。

### D4: limit

- daily + 明确多日窗：提示建议 `limit`≥50（或代码在 daily 且未指定时默认提高，如 50），避免一周被 20 截断。
- point 保持现默认 20 即可。

### D5: 确认

- history 读路径现有确认策略保持；本 change 不强制改确认话术。若 history 也走确认，确认后 `speak_history` 须带上 `history_mode`。

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| 模型漏写 history_mode | 提示强约束 + classify 后启发：含「几次/一共」且有窗则默认 daily（可选轻量后置，design 允许实现时加） |
| daily 文案偏「给 Agent」不够口语 | 先用现 compact；不足另开话术 change |
| 「最近怎么样」被误判 daily | 提示点名该句归 conversation/clinic |
| limit 仍不够 | 可再调；窗过大时如实播已拉到的行 |

## Migration Plan

1. 部署提示与透传即可。
2. 回滚：去掉 history_mode 提示约束，恢复默认 point。

## Open Questions

- （已决）「最近怎么样」归 clinic。
- 轻量后置纠偏（几次→daily）是否实现：建议实现阶段若成本低则加，不阻塞提示主路径。

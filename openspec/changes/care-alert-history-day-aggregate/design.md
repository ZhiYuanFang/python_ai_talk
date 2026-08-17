## Context

`history_compact.build_care_alert_history_prompt_blocks` 已将今昨史压成「相对时间 + 事件名 + 后缀」单条流水，并附名→id 对照表。产品希望进一步按日×事件聚合，第三段用绝对时刻列表（方案 B），总量按 time/number/one 分型书写。

## Goals / Non-Goals

**Goals:**

- 同日同 `eventName` 合并为一行：`某天·某事·时刻列表·总量`
- 计时总量可读且不歧义（`总时长XhYm`）；计数带 `eventUnit`
- 保持今昨窗口、史行无 id、legend 行为

**Non-Goals:**

- 不改拉取 `last_2_days` / 对照表策略
- 不在行内计算相邻间隔 gap（第三段仅为时刻）
- 不改 tip/clinic 的历史注入格式
- 不编写测试文件

## Decisions

1. **聚合键**：`(上海日历日 ∈ {今天,昨天}, eventName)`。同名不同 id 仍一行；legend 按名保留最近 id。
2. **第三段 = 绝对时刻（方案 B）**：组内按 `startTime` 升序，格式 `HH:MM`，`/` 拼接。不做 gap。
3. **排序**：先输出「今天」各组，再「昨天」；同日内按 `eventName` 字典序。
4. **time 总量**：Σ(end−start) 秒 → 总分钟四舍五入 → `总时长XhYm`；小时为 0 时省略 `0h`（如 `总时长45m`）；全无有效时长 → `总时长0m`。缺 end 的单次：时刻仍列，不计入时长。
5. **number 总量**：`总量{Σ eventNumber}{unit}`；unit 取 `eventUnit` / `event_unit` / `unit` 别名中组内首个非空；无单位则不加后缀。
6. **one 总量**：出现次数 `{N}次`。
7. **类型判定**：复用现有 `_event_type`（number|time|one）；一组内以组内多数或首条类型为准——**取组内第一条事件的类型**（实现简单；同名事件类型应一致）。
8. **API 形状**：将「单条 format」改为「组 format」；`build_care_alert_history_prompt_blocks` 负责分组；可保留/重命名 `format_care_alert_history_line` 为组级函数，避免误用单条语义。
9. **用户文案**：`care_alert_analyze` 中「相对次数/时间」改为说明按日聚合（时刻与总量）。

**Alternatives considered:**

- 第三段用相邻间隔：利于节奏，但产品已选时刻列表。
- 总量用 `总HH:MM`：易被读成钟点，否决，改用 `总时长XhYm`。

## Risks / Trade-offs

- [模型需自行用时刻做减法算间隔] → 提示词说明「时刻列表」即可；不额外注入 gap。
- [同名混用 time/number] → 以首条类型为准；异常数据可能总量语义偏差（可接受）。
- [未归档的 `care-alert-compact-history` 与本 delta 并存] → 本变更 MODIFIED 同一 capability 的行格式 Requirement；收版时以合并后全文为准。

## Migration Plan

- 纯提示词注入格式变更，无 API/存储迁移。
- 回滚：恢复单条流水格式化即可。

## Open Questions

- （无；探索阶段已拍板。）

## ADDED Requirements

### Requirement: Compact clock tokens MAY include remark

共享紧凑流水中，每条记录的时刻片段 SHALL 在存在非空备注时附加括号备注（例如 `08:10(AD)`）。空或仅空白备注 MUST NOT 输出括号。进行中标记 `~` 与备注并存时，`~` SHALL 紧跟时刻、位于备注括号之前（例如 `20:56~(夜醒)`）。史行仍 MUST NOT 嵌入 eventId。

#### Scenario: Remark bound to clock

- **WHEN** 某条喝奶记录 start 为当日 08:10 且 remark 为「AD」
- **THEN** 对应流水行的时刻列表中包含 `08:10(AD)`（或等价截断后的备注）

#### Scenario: Empty remark omitted

- **WHEN** 记录 remark 为空或仅空白
- **THEN** 时刻片段 SHALL 不含 `()` 备注括号

### Requirement: Local day-chain summary is prepended to history_text

`build_feeding_history_prompt_blocks`（或等价共享入口）返回的 `history_text` SHALL 在流水行之前包含本地确定性摘要块（建议标题如「【本地摘要】」）。摘要 MUST 对输入 `history_events` 中出现的**全部**上海日历日，按日序对每一对相邻日做对比。对比键 SHALL 为 `eventName`。摘要 MUST NOT 使用诊断或恐吓措辞。函数签名仍为 `(history_text, legend)`；legend 语义不变。

#### Scenario: Adjacent day delta in seven-day window

- **WHEN** 窗内含 03-17 与 03-18 的配方奶（number）与母乳（time）记录且较前日有非零增减
- **THEN** `history_text` 摘要中包含形如「03-18较03-17」的对比行
- **AND** 该行体现配方奶数量增减与母乳时长增减（单位见下述 number/time 规则）

#### Scenario: Zero delta omitted

- **WHEN** 某事件名在相邻两日的次数与计量差值均为 0
- **THEN** 该事件 MUST NOT 出现在该日对的对比子句中

#### Scenario: API shape unchanged

- **WHEN** 调用方调用共享构建函数
- **THEN** 仍收到二元组 `(history_text, legend)`
- **AND** 摘要内容位于 `history_text` 内而非第三返回值

### Requirement: Number delta units follow event unit with ml fallback

对 number 类型事件，流水总量与摘要增减所使用的单位 SHALL 取自事件字段 `eventUnit` / `unit`（组内首个非空）；当该日或该组全部记录均无单位时，SHALL 使用 `ml` 作为兜底单位。MUST NOT 在存在非空 unit 时强行改写为 ml。

#### Scenario: Unit from field

- **WHEN** 计数事件带 `eventUnit=ml` 或其它非空 unit
- **THEN** 摘要增减与流水总量使用该 unit

#### Scenario: Missing unit falls back to ml

- **WHEN** number 事件组内无任何非空 unit
- **THEN** 文案单位 SHALL 为 `ml`

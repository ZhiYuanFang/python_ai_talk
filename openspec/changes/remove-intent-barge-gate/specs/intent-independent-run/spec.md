## ADDED Requirements

### Requirement: Each intent request runs its own graph

同步与流式意图分析 MUST 用本次请求的文本进入意图图。同设备存在另一条尚未结束的意图请求时，本次请求 MUST NOT 因此挂起、等待对方终局，或把对方的回答当作本次回答返回。

#### Scenario: Second request while another is in flight

- **WHEN** 设备 D 已有一条意图分析尚未结束，同一设备再发来文本为 B 的意图分析
- **THEN** 系统 MUST 为 B 启动意图图
- **AND** MUST NOT 只返回第一条请求的终局

#### Scenario: Idle request still runs

- **WHEN** 设备 D 没有进行中的意图分析，请求文本为 A
- **THEN** 系统 MUST 以 A 启动意图图

### Requirement: Device barge buffer is not used

意图分析路径 MUST NOT 按设备读写插话缓冲，MUST NOT 因同设备已有进行中的一轮而把本句追加进缓冲，MUST NOT 在覆盖缺口时把本句与另一句拼接后重跑。

#### Scenario: Overlapping utterances are not concatenated

- **WHEN** 同一设备的两句在时间上重叠，其中一句的终局命中覆盖缺口
- **THEN** 系统 MUST NOT 因另一句还在缓冲里而拼句重跑
- **AND** 每一句 MUST 只解析自己的原话

#### Scenario: Stuck barge key does not block

- **WHEN** Redis 中仍有该设备的 `intent_barge` 键且状态为进行中
- **THEN** 新的意图分析 MUST 仍然进入意图图

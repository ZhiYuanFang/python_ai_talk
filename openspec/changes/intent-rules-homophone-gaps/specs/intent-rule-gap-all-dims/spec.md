## ADDED Requirements

### Requirement: Rule misses are recorded for every gated dimension

本地规则未命中时，系统 MUST 写入规则缺口。飞轮随后命中也 MUST 记录，且 `reason` MUST 能区分飞轮命中与调用了小模型。段原文 MUST 使用同音替换后的文本，`utterance` MUST 保留 ASR 原文。形状维 MUST NOT 单独记缺口。

#### Scenario: Flywheel hit after a rule miss is still a gap

- **WHEN** 某维本地规则未命中且飞轮命中
- **THEN** 系统 MUST 写入该维缺口且标明未调用小模型

#### Scenario: LLM path is marked

- **WHEN** 某维本地规则与飞轮都未命中并调用了小模型
- **THEN** 缺口记录 MUST 标明使用了小模型

### Requirement: Gap list returns all dimensions by default

未指定 `dimension` 时，`GET /admin/rule-gaps` MUST 返回各维度的 open 缺口，而不是只返回 `time` 与 `quantity`。每条 MUST 带 `dimension`。指定 `dimension` 时 MUST 只返回该维。

#### Scenario: Default list includes a non-time gap

- **WHEN** 存在 open 的 `predict` 缺口且请求未带 `dimension`
- **THEN** 列表结果 MUST 包含该条

### Requirement: Hub lists gaps by dimension after the Python contract

兄弟仓 Go Hub 的规则缺口页 MUST 在 Python 默认列表放开之后，按维度展示并允许筛选。MUST NOT 只渲染时间与数量两块。

#### Scenario: Operator filters one dimension

- **WHEN** 运维在 Hub 选择某一维度
- **THEN** 页面 MUST 只展示该维度的缺口

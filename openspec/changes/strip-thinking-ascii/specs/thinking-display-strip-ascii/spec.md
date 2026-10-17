## ADDED Requirements

### Requirement: LLM thinking display MUST strip Latin letters and format marks

系统经共用思考管道向客户端推送的 LLM reasoning 增量 MUST 去掉拉丁字母（`A–Z`、`a–z`）以及常见 JSON / markdown 格式符号。MUST NOT 要求过滤后的文案仍完整通顺。回答正文与图节点固定编排字幕 MUST NOT 经此剔除。

#### Scenario: English field names disappear from thinking SSE

- **WHEN** 模型思考增量中含有拉丁字母字段名或 JSON / markdown 标记
- **THEN** 对外 thinking 事件的 content MUST 不含这些拉丁字母与格式符号
- **AND** 其中的中文与数字 MAY 保留

#### Scenario: Answer body stays unchanged

- **WHEN** 同一次 LLM 调用既产出 reasoning 又产出回答正文
- **THEN** 回答正文 MUST 仍按模型原文聚合，MUST NOT 被思考字幕剔除规则改写

#### Scenario: Shared pipeline covers all collectors

- **WHEN** 任意模块经 `stream_llm_collect` 透出 LLM 思考
- **THEN** 该思考增量 MUST 经过同一套剔除
- **AND** MUST NOT 要求各智能体单独再过滤一次

#### Scenario: Empty after strip is not emitted

- **WHEN** 一段思考增量剔除后为空或仅空白
- **THEN** 系统 MUST NOT 为此推送一条空的 thinking 事件

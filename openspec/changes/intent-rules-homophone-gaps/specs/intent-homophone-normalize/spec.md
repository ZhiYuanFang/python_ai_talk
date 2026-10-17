## ADDED Requirements

### Requirement: Unique homophone span is rewritten before dimension rules

意图段解析 MUST 在各维本地规则、飞轮与小模型之前，用当前事件字典的正式名与 `extra_names` 做同音对照。仅当句中片段的带调拼音只对应一个事件词时，系统 MUST 将该片段替换为该事件词。对应零个或多个事件词时 MUST 保持该片段原文。

#### Scenario: Single event homophone is replaced

- **WHEN** 用户原文含与某一事件名同音、且字典中没有第二个事件词同音的片段
- **THEN** 后续维度解析 MUST 使用替换后的事件词
- **AND** 对外复述与十分钟对话 MUST 仍使用替换前的原文

#### Scenario: Ambiguous homophone stays

- **WHEN** 同一拼音对应两个或更多事件词
- **THEN** 系统 MUST NOT 替换该片段

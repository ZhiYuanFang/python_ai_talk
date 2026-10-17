## ADDED Requirements

### Requirement: Local rules run before flywheel on each dimension

操作轨、查记录或预测、预测格子、事件、备注、数量、时间、定位，MUST 先走本地规则。规则命中时系统 MUST NOT 再查该维飞轮，也 MUST NOT 调用该维小模型。规则未命中时 MUST 保持现有飞轮再到小模型的顺序。

#### Scenario: Predict amount is not a history read

- **WHEN** 用户说「这次要吃多少」且事件可定
- **THEN** 本地规则 MUST 将其判为预测用量
- **AND** MUST NOT 判成查记录

#### Scenario: Past quantity stays a history read

- **WHEN** 用户说「吃了多少配方奶」
- **THEN** 本地规则 MUST 将其判为查记录
- **AND** MUST NOT 判成预测用量

#### Scenario: Rule miss still reaches flywheel

- **WHEN** 某一维本地规则没有命中
- **THEN** 系统 MUST 继续该维既有飞轮与小模型路径

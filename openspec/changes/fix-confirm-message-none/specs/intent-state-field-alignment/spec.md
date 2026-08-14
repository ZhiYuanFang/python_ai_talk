## ADDED Requirements

### Requirement: IntentResult 归一容忍字符串默认字段为 null
`coerce_intent_result`（或等价图内意图结果归一入口）在接收字典入参时，对模型中类型为非 Optional 字符串、默认值为空串的字段（至少包含 `confirm_message`），若入参值为 `None`，MUST 在校验前归一为 `""`（或产生等价合法 `IntentResult`），MUST NOT 因该 null 触发 `ValidationError`。

#### Scenario: confirm_message 为 None 的字典可归一
- **WHEN** 调用方传入含 `"confirm_message": None` 的意图结果字典给 `coerce_intent_result`
- **THEN** 返回的 `IntentResult` SHALL 校验成功
- **AND** `confirm_message` SHALL 为空字符串（或与默认空串语义等价）

#### Scenario: 已有字符串值保持不变
- **WHEN** 入参字典的 `confirm_message` 为非空字符串
- **THEN** 归一后的 `IntentResult.confirm_message` SHALL 等于该字符串

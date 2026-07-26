## ADDED Requirements

### Requirement: device_no alias 声明在模型字段上
`IntentRequest`、`ClinicRequest`、`TipRequest` 的 `device_no` SHALL 在模型字段上直接使用 `Field(validation_alias=AliasChoices("device_no", "deviceNo"))` 或字段内联 `Annotated`（非共享类型别名），不得通过可复用 Annotated 类型别名携带 `validation_alias`。

#### Scenario: 导入/生成 schema 无无效 alias 警告
- **WHEN** 导入上述请求模型并生成 JSON schema
- **THEN** SHALL NOT 出现针对 device_no 的 `UnsupportedFieldAttributeWarning`（validation_alias has no effect）

#### Scenario: snake 与 camel 仍可入站
- **WHEN** JSON 使用 `device_no` 或 `deviceNo` 且其他必填合法
- **THEN** 模型校验 SHALL 成功

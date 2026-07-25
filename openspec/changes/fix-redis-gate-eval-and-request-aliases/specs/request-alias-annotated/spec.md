## ADDED Requirements

### Requirement: device_no 双收且无无效 Field 警告
`IntentRequest`、`ClinicRequest`、`TipRequest`（及同文件同类字段）SHALL 以 Pydantic 认可的方式声明 `validation_alias`（例如 `Annotated[..., Field(validation_alias=AliasChoices(...))]`），使 `device_no` 与 `deviceNo` 均可入站，且应用导入/OpenAPI 生成时 SHALL NOT 对该字段发出「validation_alias has no effect」类警告（或等价无效元数据警告）。

#### Scenario: snake_case 入站成功
- **WHEN** JSON 使用 `"device_no": "..."` 且其他必填字段合法
- **THEN** 请求模型校验 SHALL 成功，属性 `device_no` 有值

#### Scenario: camelCase 入站成功
- **WHEN** JSON 使用 `"deviceNo": "..."` 且其他必填字段合法
- **THEN** 请求模型校验 SHALL 成功，属性 `device_no` 有值

#### Scenario: 导入模型不触发无效 alias 警告
- **WHEN** 导入上述请求模型并触发生成 model schema
- **THEN** 日志/stderr SHALL NOT 出现针对该 `device_no` 字段的 `UnsupportedFieldAttributeWarning`（validation_alias）

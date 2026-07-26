## ADDED Requirements

### Requirement: device_no 使用字段级 Annotated 携带 validation_alias
`IntentRequest`、`ClinicRequest`、`TipRequest` 的 `device_no` SHALL 使用字段内联形式：

`Annotated[str, Field(validation_alias=AliasChoices("device_no", "deviceNo"), ...)]`

SHALL NOT 使用模块级可复用 Annotated 类型别名；SHALL NOT 仅用 `device_no: str = Field(..., validation_alias=...)` 作为唯一声明方式（该写法在生产 schema 路径会触发无效警告）。

#### Scenario: 导入与校验无 UnsupportedFieldAttributeWarning
- **WHEN** 导入上述模型并对合法 payload 执行 `model_validate`（含生成/访问模型字段 schema 的路径）
- **THEN** SHALL NOT 出现针对 `validation_alias` / `AliasChoices(['device_no','deviceNo'])` 的 `UnsupportedFieldAttributeWarning`

#### Scenario: snake_case 入站成功
- **WHEN** JSON 使用键 `device_no` 且其他必填合法
- **THEN** 校验 SHALL 成功且 `device_no` 有值

#### Scenario: camelCase 入站成功
- **WHEN** JSON 使用键 `deviceNo` 且其他必填合法
- **THEN** 校验 SHALL 成功且映射到 `device_no`

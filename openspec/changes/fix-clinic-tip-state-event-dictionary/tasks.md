## 1. State 通道

- [x] 1.1 在 `ClinicState` 增加 `event_dictionary: List[Dict[str, Any]]` 并更新字段说明
- [x] 1.2 在 `TipState` 同样增加 `event_dictionary` 与注释

## 2. device_no Annotated alias

- [x] 2.1 将 `IntentRequest` / `ClinicRequest` 的 `device_no` 改为字段级 `Annotated[str, Field(validation_alias=AliasChoices(...))]`
- [x] 2.2 将 `TipRequest.device_no` 改为同样字段级 Annotated 形式
- [x] 2.3 确认无模块级共享 `DeviceNoField` 类型别名

## 3. 验证

- [x] 3.1 冒烟：非空 `event_dictionary` 进入 clinic（或 judge）后 state 仍非空
- [x] 3.2 冒烟：三模型 snake/camel validate 成功，且无 `UnsupportedFieldAttributeWarning`

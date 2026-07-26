## Why

`fix-event-dictionary-wiring` 已在 clinic/tip 路由注入 `event_dictionary`，但 `ClinicState` / `TipState` TypedDict 未声明该通道。LangGraph 只保留已声明字段，注入值被静默丢弃，`judge_data_requirement` 仍读到 `[]` 并告警「事件字典为空」。同时 `device_no: str = Field(..., validation_alias=AliasChoices(...))` 在生产仍触发 `UnsupportedFieldAttributeWarning`。

## What Changes

- 在 `ClinicState`、`TipState` 增加 `event_dictionary: List[Dict[str, Any]]`（对齐 `IntentState`）
- 保留现有路由 / `call_clinic_agent` 注入逻辑不变
- 将 Intent/Clinic/Tip 请求模型的 `device_no` 改为**字段级** `Annotated[str, Field(validation_alias=AliasChoices(...))]`（勿恢复模块级共享别名），消除生产警告
- 冒烟：带非空字典进入 clinic/tip 图时，`judge_data_requirement` 可见非空 `event_dictionary`

## Capabilities

### New Capabilities

- `clinic-tip-event-dictionary-channel`: LangGraph Clinic/Tip State 声明并保留 `event_dictionary`，供共享 `judge_data_requirement` 使用
- `request-device-no-annotated-alias`: 入站请求 `device_no` 用字段级 Annotated + AliasChoices 双收，且不触发 UnsupportedFieldAttributeWarning

### Modified Capabilities

- （无主库 `openspec/specs/` 基线；本变更以新 capability 规格为准，补全上一 wiring change 遗漏的 State 通道）

## Impact

- 代码：`app/clinic/graphs/states/clinic_state.py`、`app/tip/graphs/states/tip_state.py`、`app/feeding/schemas/intent.py`、`app/tip/schemas/tip.py`
- API：HTTP 契约与 Go `data.list` 不变；clinic/tip SSE 行为不变（仅历史筛选可按真实字典收窄）
- 依赖：无新增包；需重建部署后验证

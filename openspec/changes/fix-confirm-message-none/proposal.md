## Why

用户对 `need_confirm` 回复「是的」后，确认续聊走 `leaf_intent_result` → `_execute_after_confirm` → `execute_history_crud` → `coerce_intent_result` 时，`confirm_message: None` 无法通过 Pydantic `IntentResult`（字段类型为 `str`）校验，流式接口 500。typed 图状态落地后，旧字典字面量仍写 `None`，与模型默认值语义不一致。

## What Changes

- 确认落叶子 / 管线清确认态时，字符串确认字段 MUST 使用空串而非 `None`（至少 `confirm_message`）。
- `coerce_intent_result` MUST 容忍入参字典中字符串默认字段为 `None`（归一为默认空串），避免确认后 CRUD 因校验崩溃。
- 不改变确认话术文案、pending 存取协议或对外 API 字段语义（缺省仍视为无确认文案）。

## Capabilities

### New Capabilities

- （无）

### Modified Capabilities

- `feeding-intent-user-confirmation`: 用户确认后继续执行落库/历史 CRUD 时 MUST NOT 因 `confirm_message` 为 `None` 导致校验失败或 HTTP 500。
- `intent-state-field-alignment`: `IntentResult` 归一入口 MUST 接受常见「可选空串字段被写成 null」的字典，并稳定产出合法模型。

## Impact

- `app/feeding/services/clarification.py`（`leaf_intent_result`）
- `app/feeding/services/intent_pipeline.py`（清确认态字典）
- `app/feeding/schemas/intent_result.py`（`coerce_intent_result` 或字段定义）
- 确认续聊 → `execute_history_crud` / 喂养落库主路径
- 无兄弟仓 API 破坏性变更

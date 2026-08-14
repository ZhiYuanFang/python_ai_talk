## 1. 源头清态

- [x] 1.1 将 `leaf_intent_result` 中 `confirm_message` 从 `None` 改为 `""`
- [x] 1.2 将 `intent_pipeline` 清确认态字典中的 `confirm_message: None` 改为 `""`
- [x] 1.3 全仓 grep `confirm_message` 与 `None` 同写，消除喂养确认主路径残留

## 2. 归一容错

- [x] 2.1 在 `coerce_intent_result` 中对非 Optional 默认空串字段（至少 `confirm_message`）将入参 `None` 归一为 `""` 后再 `model_validate`
- [x] 2.2 必要时补简短中文注释说明为何容忍 null

## 3. 验收

- [x] 3.1 手工验证：结束睡眠 need_confirm → 回复「是的」+ conversation_id，意图流式不再因 ValidationError 500
- [x] 3.2 `openspec validate fix-confirm-message-none --strict`

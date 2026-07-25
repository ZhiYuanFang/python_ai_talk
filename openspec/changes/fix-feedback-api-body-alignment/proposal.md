## Why

Go 侧 `PythonAIClient.submitFeedback()` 方法通过 JSON Body 发送 `{"answer_id": "xxx", "feedback": 1}` 到 Python 的 feedback 接口，但 Python 侧 `clinic_feedback()` 和 `tip_feedback()` 函数签名使用 `(answer_id: str, feedback: int)`，FastAPI 默认将其解析为 Query 参数。两边参数位置不匹配，导致 Go 调用反馈接口时失败。

## What Changes

- 在 `app/shared/schemas/` 下新增共享的 `FeedbackRequest` Pydantic 模型
- Python 侧 `clinic_feedback()` 和 `tip_feedback()` 两个接口函数签名改为接收 Pydantic Body 模型
- 将 feedback 值的校验（只能是 1 或 -1）从函数体逻辑移到 Pydantic validator
- Go 侧代码不需要改动（已正确使用 JSON Body）

## Capabilities

### New Capabilities

无（本次变更是接口对齐修复，不涉及新功能）

### Modified Capabilities

- `/v1/clinic/feedback` 接口：参数接收方式从 Query 参数改为 JSON Body
- `/v1/tip/feedback` 接口：参数接收方式从 Query 参数改为 JSON Body

## Impact

- **受影响的文件**：
  - `app/api/routes/clinic.py` — 修改 `clinic_feedback()` 函数签名和内部逻辑
  - `app/api/routes/tip.py` — 修改 `tip_feedback()` 函数签名和内部逻辑
- **需要新增的文件**：
  - `app/shared/schemas/__init__.py`
  - `app/shared/schemas/feedback.py` — 定义 `FeedbackRequest` Pydantic 模型
- **向后兼容性**：
  - 接口 URL 不变，仍为 POST `/v1/clinic/feedback` 和 POST `/v1/tip/feedback`
  - 请求体格式与 Go 侧完全一致：`{"answer_id": "xxx", "feedback": 1}`
  - 响应格式不变
  - **破坏性变更**：原来通过 Query 参数调用的方式将不再支持（但 Go 侧本来就是 JSON Body，所以实际无影响）

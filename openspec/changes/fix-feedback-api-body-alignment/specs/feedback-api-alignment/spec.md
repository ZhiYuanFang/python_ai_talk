## MODIFIED Requirements

### Requirement: Feedback 接口参数格式对齐

Python 服务的两个 feedback 接口 SHALL 接收 JSON Body 格式的请求参数，与 Go 侧 `PythonAIClient.submitFeedback()` 的发送方式保持一致。

#### Scenario: Go 侧调用诊疗反馈接口
- **WHEN** Go 服务通过 `POST /v1/clinic/feedback` 发送 `Content-Type: application/json` 的请求，Body 为 `{"answer_id": "clinic_xxx", "feedback": 1}`
- **THEN** Python 服务 SHALL 正确解析 JSON Body 中的 `answer_id` 和 `feedback` 字段
- **AND** Python 服务 SHALL 正常执行反馈逻辑（频率限制检查、质量分更新）
- **AND** Python 服务 SHALL 返回 `{"code": 0, "message": "反馈成功", "data": {"answer_id": "...", "feedback": 1}}`

#### Scenario: Go 侧调用小贴士反馈接口
- **WHEN** Go 服务通过 `POST /v1/tip/feedback` 发送 `Content-Type: application/json` 的请求，Body 为 `{"answer_id": "tip_xxx", "feedback": -1}`
- **THEN** Python 服务 SHALL 正确解析 JSON Body 中的 `answer_id` 和 `feedback` 字段
- **AND** Python 服务 SHALL 正常执行反馈逻辑（频率限制检查、质量分更新）
- **AND** Python 服务 SHALL 返回 `{"code": 0, "message": "反馈成功", "data": {"answer_id": "...", "feedback": -1}}`

### Requirement: Feedback 参数校验

Feedback 接口的 `feedback` 字段 SHALL 只能为 `1`（👍）或 `-1`（👎），不合法的值 SHALL 在请求解析阶段被拒绝。

#### Scenario: feedback 值不合法
- **WHEN** 调用 feedback 接口时传入 `feedback: 2` 或其他非 1/-1 的值
- **THEN** Python 服务 SHALL 返回 422 状态码（参数校验失败）
- **AND** 不执行任何后续的反馈逻辑（频率限制、质量分更新等）

### Requirement: 共享 Pydantic 模型

`FeedbackRequest` 数据模型 SHALL 定义在 `app/shared/schemas/` 共享目录下，clinic 和 tip 两个模块 SHALL 复用同一个模型。

#### Scenario: 共享模型复用
- **WHEN** `clinic_feedback()` 和 `tip_feedback()` 接收请求参数
- **THEN** 两个函数 SHALL 使用同一个 `FeedbackRequest` Pydantic 模型
- **AND** 该模型 SHALL 可从 `app.shared.schemas.feedback` 模块导入

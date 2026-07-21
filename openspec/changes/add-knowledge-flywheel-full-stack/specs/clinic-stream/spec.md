## MODIFIED Requirements

### Requirement: 诊疗流式响应格式
系统 SHALL 在诊疗流式响应中新增 done 事件，包含 answerId 字段。

#### Scenario: 流式响应包含 thinking 事件
- **WHEN** 诊疗 LLM 正在思考
- **THEN** 系统发送 `{"type": "thinking", "content": "..."}` 事件

#### Scenario: 流式响应包含 answer 事件
- **WHEN** 诊疗 LLM 生成回答内容
- **THEN** 系统发送 `{"type": "answer", "content": "..."}` 事件

#### Scenario: 流式响应包含 done 事件（新增）
- **WHEN** 诊疗回答生成完成
- **THEN** 系统发送 `{"type": "done", "answerId": <id>}` 事件，其中 <id> 为诊疗会话的数据库 ID

## ADDED Requirements

### Requirement: Go 侧 TipStream 客户端
Go 服务 SHALL 在 `PythonAIClient` 中新增 `TipStream` 方法，调用 Python 的 `/v1/tip/stream` 接口。

#### Scenario: Go 调用 Python 生成小贴士
- **WHEN** Go 服务接收到事件触发小贴士生成
- **THEN** `PythonAIClient.TipStream` 方法调用 Python `/v1/tip/stream` 接口，获取 SSE 流式响应

### Requirement: Go 侧诊疗反馈接口
Go 服务 SHALL 提供 `/clinic/feedback` 接口，接收 Flutter 客户端的诊疗反馈，并同步到 Python 服务。

#### Scenario: Flutter 提交诊疗反馈
- **WHEN** Flutter 客户端调用 Go 的 `/clinic/feedback` 接口
- **THEN** Go 服务将反馈写入数据库，并调用 Python 的 `/v1/clinic/feedback` 接口

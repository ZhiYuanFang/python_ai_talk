## MODIFIED Requirements

### Requirement: 诊疗流式接口实现方式
诊疗流式接口 `/v1/clinic/stream` SHALL 使用 LangGraph StateGraph 编排替代手写逻辑，并增加动态历史范围判断能力。

#### Scenario: 使用 LangGraph 编排
- **WHEN** 接收到诊疗请求
- **THEN** 系统 SHALL 调用 clinic_graph 执行诊疗流程
- **AND** 不 SHALL 使用手写函数调用链处理流程

#### Scenario: 动态判断历史范围
- **WHEN** 用户提交诊疗问题"宝宝最近吃得少怎么办"
- **THEN** 系统 SHALL 先调用 LLM 判断需要的事件ID和时间范围
- **AND** 根据判断结果调用 filter API 拉取对应历史记录
- **AND** 不 SHALL 拉取全量历史记录

#### Scenario: SSE 流式响应格式不变
- **WHEN** clinic_graph 返回流式结果
- **THEN** SSE 事件格式 SHALL 保持不变（type: thinking/answer, content: 内容）
- **AND** 前端无需任何修改

#### Scenario: 诊疗系统提示词内容不变
- **WHEN** 构建 clinic 场景的系统提示词
- **THEN** 提示词内容 SHALL 复用 go_ai_talk 的 aiClinic.systemPrompt
- **AND** 仍包含宝宝信息、历史记录、相关知识三个上下文部分

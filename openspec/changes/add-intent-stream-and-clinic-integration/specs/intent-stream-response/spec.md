## ADDED Requirements

### Requirement: 系统支持 intent 流式响应
系统 SHALL 支持通过 `/v1/analyze/intent/stream` 端点以 SSE 方式流式返回意图分析结果。

#### Scenario: 非流式请求（默认）
- **WHEN** 客户端调用 `/v1/analyze/intent`
- **THEN** 系统返回 JSON 格式的意图分析结果
- **AND** 不暴露节点执行进度

#### Scenario: 流式请求
- **WHEN** 客户端调用 `/v1/analyze/intent/stream`
- **THEN** 系统通过 SSE 返回 thinking 事件
- **AND** 每个节点执行时发送 thinking 事件
- **AND** 最终发送 answer 事件包含意图结果

### Requirement: 流式响应暴露节点思考进度
系统 SHALL 在流式响应中通过 thinking 事件暴露每个节点的执行进度。

#### Scenario: 向量匹配节点进度
- **WHEN** 执行 match_event_by_vector 节点
- **THEN** 发送 thinking 事件：`{"node": "match_event_by_vector", "message": "正在匹配喂养事件...", "status": "running"}`

#### Scenario: LLM 分类节点进度
- **WHEN** 执行 classify_intent 节点
- **THEN** 发送 thinking 事件：`{"node": "classify_intent", "message": "正在分析意图...", "status": "running"}`

#### Scenario: 确认话术节点进度
- **WHEN** 执行 prepare_confirm 节点
- **THEN** 发送 thinking 事件：`{"node": "prepare_confirm", "message": "正在生成确认话术...", "status": "running"}`

#### Scenario: clinic agent 调用节点进度
- **WHEN** 执行 call_clinic_agent 节点
- **THEN** 发送 thinking 事件：`{"node": "call_clinic_agent", "message": "正在获取喂养建议...", "status": "running"}`

### Requirement: 流式响应最终返回意图结果
系统 SHALL 在所有节点执行完成后，通过 answer 事件返回最终意图结果。

#### Scenario: 返回意图结果
- **WHEN** 所有节点执行完成
- **THEN** 发送 answer 事件，包含完整的意图分析结果
- **AND** 关闭 SSE 连接

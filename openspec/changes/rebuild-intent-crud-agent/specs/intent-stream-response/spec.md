## MODIFIED Requirements

### Requirement: 系统支持 intent 流式响应
系统 SHALL 支持通过 `/v1/analyze/intent/stream` 端点以 SSE 方式流式返回意图分析结果。非流式 `/v1/analyze/intent` SHALL 返回同一套意图图的 JSON 结果（无 thinking 事件）。两入口 MUST NOT 一个走 clinic、一个走意图图。

#### Scenario: 非流式请求（默认）
- **WHEN** 客户端调用 `/v1/analyze/intent`
- **THEN** 系统返回 JSON 格式的意图分析结果
- **AND** 不暴露节点执行进度
- **AND** 业务语义与 stream 最终 answer 一致

#### Scenario: 流式请求
- **WHEN** 客户端调用 `/v1/analyze/intent/stream`
- **THEN** 系统通过 SSE 返回 thinking 事件
- **AND** 每个相关节点执行时发送 thinking 事件
- **AND** 最终发送 answer 事件包含意图结果

### Requirement: 流式响应暴露节点思考进度
系统 SHALL 在流式响应中通过 thinking 事件暴露意图图节点的执行进度。

#### Scenario: 意图缓存或向量匹配节点进度
- **WHEN** 执行意图缓存匹配或事件向量匹配节点
- **THEN** 发送 thinking 事件，`node` 为实际节点名，`status` 为 running

#### Scenario: LLM 分类节点进度
- **WHEN** 执行 classify_intent 节点
- **THEN** 发送 thinking 事件：节点为 `classify_intent`，`status` 为 `running`

#### Scenario: 历史执行节点进度
- **WHEN** 执行 Python 历史 CRUD 或查记录生成节点
- **THEN** 发送对应节点的 thinking 事件
- **AND** SHALL NOT 再发送 `call_clinic_agent` 节点进度

### Requirement: 流式响应最终返回意图结果
系统 SHALL 在所有节点执行完成后，通过 answer 事件返回最终意图结果，其字段语义 SHALL 与非流式 `IntentResponse` 一致（含 `content`、`op`、`events`、`need_confirm`）。

#### Scenario: 返回意图结果
- **WHEN** 所有节点执行完成
- **THEN** 发送 answer 事件，包含完整的意图分析结果
- **AND** 关闭 SSE 连接

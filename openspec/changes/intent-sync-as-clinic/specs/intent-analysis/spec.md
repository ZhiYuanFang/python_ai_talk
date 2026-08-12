## MODIFIED Requirements

### Requirement: 意图分析接口

系统 SHALL 提供 `/v1/analyze/intent` HTTP POST 接口，接收自然语言文本和设备编号。对该非流式端点，系统 SHALL 直接调用 clinic agent（与意图图中的 `call_clinic_agent` 同等能力：陪伴会话、clinic 数据准备、同步生成），并返回 `IntentResponse`；SHALL NOT 在该非流式端点执行喂养意图分类、向量匹配、pending 澄清或父事件消歧。响应的 `target_type` SHALL 为 `conversation`，`action` SHALL 为 `reply`，`content` SHALL 为 clinic 生成的回答文本（失败时可为兜底文案）。URL 与请求字段（含 `text`、`device_no`、可选 `model`）SHALL 保持不变以兼容既有前端。

#### Scenario: 非流式成功返回陪伴回答

- **WHEN** 客户端发送 POST 请求到 `/v1/analyze/intent`，body 包含有效的 `text` 与 `device_no`（及可选 `model`）
- **THEN** 服务返回 HTTP 200
- **AND** 响应 `target_type` 为 `conversation`、`action` 为 `reply`
- **AND** 响应 `content` 为非空的 clinic 回答或约定兜底文案

#### Scenario: 非流式不再返回喂养结构

- **WHEN** 客户端发送 POST 请求到 `/v1/analyze/intent`，body 的 `text` 为「开始喂奶」
- **THEN** 服务 MUST NOT 以喂养落库语义返回 `target_type=feeding`
- **AND** 仍按陪伴路径返回 `conversation`/`reply` 与 `content`

#### Scenario: 失败 - 缺少必要参数

- **WHEN** 客户端发送 POST 请求到 `/v1/analyze/intent`，body 缺少 `text` 或 `device_no` 字段
- **THEN** 服务返回 HTTP 400，响应 body 包含错误信息

### Requirement: 意图分析接口实现方式

非流式意图分析接口 `/v1/analyze/intent` SHALL 直接调用 clinic agent 路径，SHALL NOT 再为该非流式请求调用 `intent_graph` 做意图分类与喂养后处理。`/v1/analyze/intent/stream` 的实现方式不在本 Requirement 中变更。

#### Scenario: 非流式不走 intent_graph

- **WHEN** 接收到非流式 `/v1/analyze/intent` 请求
- **THEN** 系统 SHALL 调用 clinic agent（`call_clinic_agent` 或等价共享实现）生成回答
- **AND** SHALL NOT 调用 `intent_graph.ainvoke` 完成该请求

## MODIFIED Requirements

### Requirement: 系统分析用户输入的意图
系统 SHALL 分析用户输入，识别其意图类型，并支持流式返回和内部调用 clinic agent。

#### Scenario: 喂养建议意图内部调用 clinic agent
- **WHEN** 意图识别为 conversation 或 suggest
- **THEN** 系统内部调用 clinic_graph 获取回答
- **AND** 将 clinic 回答作为意图结果的内容返回
- **AND** 不需要前端发起二次请求

#### Scenario: 流式请求暴露所有节点进度
- **WHEN** 客户端请求流式响应
- **THEN** 系统在每个节点执行时发送 thinking 事件
- **AND** 包括向量匹配、LLM 分类、确认、clinic agent 调用等节点

#### Scenario: 非流式请求保持兼容
- **WHEN** 客户端请求非流式响应（默认）
- **THEN** 系统返回 JSON 格式结果
- **AND** 内部仍调用 clinic agent 获取回答

## MODIFIED Requirements

### Requirement: clinic_graph 状态图结构
系统 SHALL 使用 LangGraph StateGraph 构建诊疗流程图（clinic_graph）。图 MUST NOT 包含 `implicit_feedback`、Q&A 捷径节点（rewrite / search_qa / format_qa）或通识 `search_vectors`。准备与回答链路 SHALL 在无通识检索、无隐式飞轮的前提下完成（可含月龄/画像、按需历史与流式生成等既有非飞轮节点）。

#### Scenario: clinic_graph 不含已删飞轮节点
- **WHEN** 构建 clinic_graph
- **THEN** 图 MUST NOT 注册 `implicit_feedback`、`search_qa_fast_path` 或通识 `search_vectors` 节点

#### Scenario: clinic_graph 仍可流式回答
- **WHEN** 收到合法 clinic 流式请求
- **THEN** 路由仍可经 clinic_graph 产出回答 SSE（无 Q&A 早停、无通识注入）

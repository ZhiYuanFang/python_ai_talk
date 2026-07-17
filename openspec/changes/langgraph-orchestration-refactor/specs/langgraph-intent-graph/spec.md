## ADDED Requirements

### Requirement: intent_graph 状态图结构
系统 SHALL 使用 LangGraph StateGraph 构建意图分析流程图（intent_graph），包含意图分类→条件路由→后处理完整链路。

#### Scenario: intent_graph 节点组成
- **WHEN** 构建 intent_graph
- **THEN** 图 SHALL 包含以下节点：classify_intent、judge_data_requirement、fetch_history、search_vectors、fetch_baby_profile、generate_response
- **AND** 图 SHALL 包含条件边，根据 intent_result.target_type 路由到不同分支

#### Scenario: feeding 意图路由
- **WHEN** classify_intent 节点返回 target_type=feeding
- **THEN** 图 SHALL 直接返回 IntentResponse，不执行后处理节点
- **AND** 不调用 judge_data_requirement、fetch_history 等节点

#### Scenario: history 意图路由
- **WHEN** classify_intent 节点返回 target_type=history
- **THEN** 图 SHALL 依次执行 judge_data_requirement → fetch_history → generate_response 节点

#### Scenario: suggest 意图路由
- **WHEN** classify_intent 节点返回 target_type=suggest
- **THEN** 图 SHALL 依次执行 judge_data_requirement → fetch_history → search_vectors → fetch_baby_profile → generate_response 节点

#### Scenario: conversation 意图路由
- **WHEN** classify_intent 节点返回 target_type=conversation
- **THEN** 图 SHALL 直接返回兜底文案，不执行后处理节点

#### Scenario: exit 意图路由
- **WHEN** classify_intent 节点返回 target_type=exit
- **THEN** 图 SHALL 直接返回 IntentResponse，不执行后处理节点

### Requirement: IntentState 定义
intent_graph SHALL 使用独立的 IntentState 类定义状态字段。

#### Scenario: IntentState 字段完整性
- **WHEN** 定义 IntentState
- **THEN** SHALL 包含以下字段：user_input (str)、device_no (str)、model_config (dict)、event_dictionary (list)、intent_result (dict)、data_requirement (dict)、history_events (list)、knowledge (list)、baby_profile (dict)、response (str)

### Requirement: intent_graph 与路由集成
路由文件 `routes/intent.py` SHALL 调用 intent_graph 执行意图分析，替代当前手写逻辑。

#### Scenario: 路由调用 graph
- **WHEN** 接收到 /v1/analyze/intent 请求
- **THEN** 路由 SHALL 构建 IntentState 输入
- **AND** 调用 intent_graph.invoke() 执行流程
- **AND** 从最终状态提取 IntentResponse 返回

### Requirement: intent_graph 兼容性
intent_graph 的返回结果 SHALL 与当前 analyze_intent 接口的返回格式完全兼容。

#### Scenario: 返回格式兼容
- **WHEN** intent_graph 执行完成
- **THEN** 返回的 IntentResponse SHALL 包含 target_type、action、event_name、keywords、content 字段
- **AND** 字段类型和语义 SHALL 与原有接口一致

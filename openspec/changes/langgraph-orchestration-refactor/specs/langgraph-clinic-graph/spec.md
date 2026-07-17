## ADDED Requirements

### Requirement: clinic_graph 状态图结构
系统 SHALL 使用 LangGraph StateGraph 构建诊疗流程图（clinic_graph），包含数据需求判断→按需拉取历史→向量检索→流式回答完整链路。

#### Scenario: clinic_graph 节点组成
- **WHEN** 构建 clinic_graph
- **THEN** 图 SHALL 包含以下节点：judge_data_requirement、fetch_history、search_vectors、fetch_baby_profile、stream_response

#### Scenario: clinic_graph 流程顺序
- **WHEN** clinic_graph 执行
- **THEN** 节点执行顺序 SHALL 为：judge_data_requirement → fetch_history → search_vectors → fetch_baby_profile → stream_response

#### Scenario: clinic_graph 动态判断历史范围
- **WHEN** clinic_graph 执行 fetch_history 节点
- **THEN** SHALL 先通过 judge_data_requirement 节点判断需要的事件ID和时间范围
- **AND** 根据判断结果调用 filter API 拉取对应历史记录
- **AND** 不 SHALL 拉取全量历史记录

### Requirement: ClinicState 定义
clinic_graph SHALL 使用独立的 ClinicState 类定义状态字段。

#### Scenario: ClinicState 字段完整性
- **WHEN** 定义 ClinicState
- **THEN** SHALL 包含以下字段：question (str)、device_no (str)、model_config (dict)、data_requirement (dict)、history_events (list)、knowledge (list)、baby_profile (dict)

### Requirement: clinic_graph 与路由集成
路由文件 `routes/clinic.py` SHALL 调用 clinic_graph 执行诊疗流程，替代当前手写逻辑。

#### Scenario: 路由调用 graph
- **WHEN** 接收到 /v1/clinic/stream 请求
- **THEN** 路由 SHALL 构建 ClinicState 输入
- **AND** 调用 clinic_graph.astream() 执行流程
- **AND** 将流式结果转换为 SSE 事件返回

#### Scenario: SSE 事件格式兼容
- **WHEN** clinic_graph 返回流式结果
- **THEN** 转换后的 SSE 事件 SHALL 包含 type（thinking 或 answer）和 content 字段
- **AND** 格式 SHALL 与原有 clinic_stream 接口一致

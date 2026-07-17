## ADDED Requirements

### Requirement: 节点文件组织
所有 LangGraph 节点 SHALL 遵循一节点一文件原则，存放在 `app/graphs/nodes/` 目录。

#### Scenario: 节点文件结构
- **WHEN** 查看 `app/graphs/nodes/` 目录
- **THEN** SHALL 包含以下文件：classify_intent.py、judge_data_requirement.py、fetch_history.py、search_vectors.py、fetch_baby_profile.py、generate_response.py、stream_response.py
- **AND** 每个文件 SHALL 只包含一个节点函数及其辅助逻辑

### Requirement: 节点纯函数设计
每个节点 SHALL 为纯函数，输入 State，返回 State 的部分更新字典。

#### Scenario: 节点输入输出规范
- **WHEN** 实现一个节点函数
- **THEN** 函数 SHALL 接收 State 对象作为参数
- **AND** 函数 SHALL 返回 dict，包含需要更新的 State 字段
- **AND** 函数 SHALL 不直接修改输入的 State 对象

### Requirement: fetch_history 节点
fetch_history 节点 SHALL 根据 data_requirement 判断是否使用 filter API。

#### Scenario: 有数据需求判断结果时使用 filter API
- **WHEN** state.data_requirement 包含 event_ids 或 time_range
- **THEN** 节点 SHALL 调用 `http_client.get_filtered_history_events` 方法
- **AND** 传入 event_ids、start_time、end_time、limit 参数

#### Scenario: 无数据需求判断结果时使用全量 API
- **WHEN** state.data_requirement 为空或 None
- **THEN** 节点 SHALL 调用 `http_client.get_history_events` 方法
- **AND** 仅传入 device_no 参数

#### Scenario: filter API 不可用时降级
- **WHEN** 调用 `get_filtered_history_events` 返回 HTTP 错误
- **THEN** 节点 SHALL 降级调用 `get_history_events` 拉取全量数据
- **AND** 记录降级日志

### Requirement: judge_data_requirement 节点
judge_data_requirement 节点 SHALL 调用 LLM 判断需要拉取的历史数据范围。

#### Scenario: LLM 正常返回
- **WHEN** LLM 返回合法的 JSON（包含 event_ids 和 time_range）
- **THEN** 节点 SHALL 将结果存入 state.data_requirement
- **AND** 验证 event_ids 中的 ID 在事件字典中存在

#### Scenario: LLM 返回格式错误
- **WHEN** LLM 返回的 JSON 格式无效
- **THEN** 节点 SHALL 使用默认配置：event_ids 为空、time_range 为 "last_7_days"
- **AND** 记录警告日志

#### Scenario: LLM 返回未知时间范围
- **WHEN** LLM 返回的 time_range 不在可选值列表中
- **THEN** 节点 SHALL 使用默认时间范围：last_7_days

#### Scenario: LLM 返回不存在的事件ID
- **WHEN** LLM 返回的 event_ids 不在事件字典中
- **THEN** 节点 SHALL 忽略该事件ID，保留有效的事件ID
- **AND** 如果所有事件ID都无效，使用空列表

### Requirement: search_vectors 节点
search_vectors 节点 SHALL 调用向量库检索相关知识。

#### Scenario: 使用用户问题检索
- **WHEN** search_vectors 节点执行
- **THEN** 节点 SHALL 使用 state.user_input（intent_graph）或 state.question（clinic_graph）作为查询词
- **AND** 调用 `vector_store.search` 方法，n_results=5
- **AND** 将结果存入 state.knowledge

#### Scenario: 向量库检索失败
- **WHEN** vector_store.search 抛出异常
- **THEN** 节点 SHALL 将 state.knowledge 设为空列表
- **AND** 记录错误日志，不中断流程

### Requirement: fetch_baby_profile 节点
fetch_baby_profile 节点 SHALL 调用 Go 侧 API 获取宝宝画像。

#### Scenario: 正常获取宝宝画像
- **WHEN** fetch_baby_profile 节点执行
- **THEN** 节点 SHALL 调用 `http_client.get_baby_profile` 方法
- **AND** 将结果存入 state.baby_profile

#### Scenario: 宝宝画像不存在
- **WHEN** get_baby_profile 返回 None
- **THEN** 节点 SHALL 将 state.baby_profile 设为空字典
- **AND** 不中断流程

### Requirement: generate_response 节点
generate_response 节点 SHALL 根据意图类型和历史数据，调用 LLM 生成回答。

#### Scenario: history 意图生成回答
- **WHEN** state.intent_result.target_type 为 history
- **THEN** 节点 SHALL 使用 history_answer 提示词
- **AND** 将历史记录作为上下文传入 LLM
- **AND** 将 LLM 回答存入 state.response

#### Scenario: suggest 意图生成建议
- **WHEN** state.intent_result.target_type 为 suggest
- **THEN** 节点 SHALL 使用 suggest_answer 提示词
- **AND** 将历史记录、向量检索结果、宝宝画像作为上下文传入 LLM
- **AND** 将 LLM 回答存入 state.response

### Requirement: stream_response 节点
stream_response 节点 SHALL 流式调用 LLM，返回诊疗回答。

#### Scenario: 流式生成诊疗回答
- **WHEN** stream_response 节点执行
- **THEN** 节点 SHALL 使用 clinic_answer 提示词
- **AND** 将历史记录、向量检索结果、宝宝画像作为上下文
- **AND** 流式调用 LLM，yield 每个 chunk
- **AND** 支持 thinking 模式（分离思考和回答内容）

### Requirement: classify_intent 节点
classify_intent 节点 SHALL 调用 LLM 进行意图分类。

#### Scenario: 意图分类流程
- **WHEN** classify_intent 节点执行
- **THEN** 节点 SHALL 获取事件字典
- **AND** 使用 intent_classification 提示词
- **AND** 调用 LLM 进行意图分类
- **AND** 解析 LLM 返回的 JSON，存入 state.intent_result

#### Scenario: 喂养场景事件名匹配
- **WHEN** classify_intent 返回 target_type=feeding 且 event_name 为空
- **THEN** 节点 SHALL 根据用户文本匹配事件字典中的关键词
- **AND** 填充 event_name 字段

#### Scenario: 对话场景兜底文案
- **WHEN** classify_intent 返回 target_type=conversation 且 content 为空
- **THEN** 节点 SHALL 使用预设的兜底文案填充 content 字段

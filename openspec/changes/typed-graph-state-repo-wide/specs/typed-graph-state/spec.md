## ADDED Requirements

### Requirement: 四图 State 须为 Pydantic 模型
`intent_graph`、`clinic_graph`、`tip_graph`、`care_alert_graph`（或等价 care-alert 编排入口）的 State 类型 MUST 为 Pydantic `BaseModel`（允许各模块命名为 `IntentState`/`ClinicState`/`TipState`/`CareAlertState`）。系统 MUST NOT 以未建模的匿名 `dict` 作为上述图的主路径初始 State 构造方式。路由或 analyze 服务构造初始 State 时 SHALL 使用模型构造函数（关键字参数赋值）。

#### Scenario: intent 冷启动构造
- **WHEN** `/v1/analyze/intent` 冷启动进入 `intent_graph`
- **THEN** 初始 State SHALL 为 Pydantic 意图 State 实例（或经单一边界序列化，但源构造 MUST 为模型）
- **AND** SHALL 通过字段赋值提供 `user_input`、`device_no`、事件字典与 `conversation_id`（若适用）

#### Scenario: clinic/tip/care-alert 入口同类
- **WHEN** clinic、tip 或 care-alert 分析进入对应图
- **THEN** 初始 State SHALL 同样以该图 Pydantic State 构造
- **AND** MUST NOT 以散落字符串 key 的匿名 dict 字面量作为唯一构造源

### Requirement: 节点读写与补丁合并
图节点 SHALL 以对应 Pydantic State（或共享 Protocol）读取字段属性。节点写回 SHALL 返回字段补丁；编排层 MUST 将补丁合并进 State，且 MUST NOT 因合并实现丢弃 State 上已存在、补丁未提及的已注入字段（例如 `event_dictionary`）。

#### Scenario: 补丁不擦除事件字典
- **WHEN** 初始 State 含非空 `event_dictionary`，随后某节点仅返回其它字段补丁
- **THEN** 合并后的 State.`event_dictionary` SHALL 仍为非空

#### Scenario: 属性读取
- **WHEN** `classify_intent`（或等价意图分类节点）执行
- **THEN** SHALL 从 State 属性读取 `user_input` 与 `model_config`（不得仅依赖已删除的并行 dict 钥匙作为主路径）

### Requirement: 共享节点以 Protocol 声明依赖字段
`app/shared/graphs` 下跨 clinic/tip/care-alert（及 intent 若复用）的节点 MUST 以 typing `Protocol`（或等价结构子类型）声明所需字段，MUST NOT 硬编码依赖某一业务模块的完整 State 类以致 feeding↔clinic 互引。

#### Scenario: fetch_history 不导入 clinic State
- **WHEN** 实现或调用共享 `fetch_history`
- **THEN** 其类型注解 SHALL 不要求导入 `ClinicState` 作为唯一合法输入类型
- **AND** 具备 `device_no` 与数据需求字段的 tip/care-alert State 仍可调用

### Requirement: IntentResult 与 DataRequirement 模型化
意图图主路径中的意图结果 MUST 使用 Pydantic `IntentResult`（名称以实现为准）承载，MUST NOT 以无模式的 `Dict[str, Any]` 作为分类/备注反查/确认管线的主存储类型。clinic/tip/care-alert 用于驱动拉史的数据需求 MUST 使用 Pydantic `DataRequirement`（名称以实现为准）。care-alert 的 `items` SHALL 使用既有条目 DTO 类型列表。

#### Scenario: 分类产出 IntentResult
- **WHEN** `classify_intent` 成功解析 LLM JSON
- **THEN** 写入 State 的意图结果 SHALL 为 `IntentResult` 实例（或等价模型）
- **AND** 后续备注反查与确认管线 SHALL 能按字段读写 `op`、`event_id`、`remark_keyword` 等

#### Scenario: judge 产出 DataRequirement
- **WHEN** `judge_data_requirement` 完成
- **THEN** State 上的数据需求 SHALL 为 `DataRequirement` 实例
- **AND** `fetch_history` SHALL 从该模型字段读取筛选条件

### Requirement: 流式终态合并保持模型语义
经 `astream`/`iter_graph_custom_thinking`（或等价）合并 updates 得到的终态 MUST 保持与非流式 `ainvoke` 相同的 Pydantic State 字段语义，MUST NOT 因 dict 合并丢失已声明通道。

#### Scenario: intent 流式与非流式字段一致
- **WHEN** 同一冷启动输入分别走非流式 `ainvoke` 与流式 thinking 消费
- **THEN** 终态中的 `user_input`、事件字典与意图结果关键字段语义 SHALL 一致（允许实例 vs dump 的表示差，语义 MUST 等价）

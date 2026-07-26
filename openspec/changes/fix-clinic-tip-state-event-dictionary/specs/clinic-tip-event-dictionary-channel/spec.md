## ADDED Requirements

### Requirement: ClinicState 声明事件字典通道
`ClinicState` SHALL 包含字段 `event_dictionary: List[Dict[str, Any]]`（TypedDict，与 `IntentState` 同名同义），使 LangGraph 在图执行期间保留路由或嵌套调用写入的事件字典。

#### Scenario: 非空字典进入 clinic 图后仍可见
- **WHEN** 以含非空 `event_dictionary` 的初始 state 执行 `clinic_graph`（或至少执行到 `judge_data_requirement`）
- **THEN** 该节点读到的 `state["event_dictionary"]` SHALL 为非空列表
- **AND** SHALL NOT 仅因 State 未声明通道而打印「事件字典为空，使用默认数据需求」

### Requirement: TipState 声明事件字典通道
`TipState` SHALL 同样声明 `event_dictionary`，使 tip 图中依赖该字段的共享节点（含 `judge_data_requirement`）能读到路由注入值。

#### Scenario: 非空字典进入 tip 图后仍可见
- **WHEN** 以含非空 `event_dictionary` 的初始 state 执行 tip 路径至 `judge_data_requirement`
- **THEN** 该节点读到的 `event_dictionary` SHALL 为非空列表

### Requirement: 未声明通道不得再成为空字典根因
在路由已注入且缓存返回非空的前提下，clinic/tip 的「事件字典为空」告警 SHALL NOT 由 TypedDict 缺字段导致。

#### Scenario: 注入成功时不应误报空
- **WHEN** `event_cache.get_event_dictionary()` 返回非空且路由写入 initial_state
- **THEN** clinic/tip 图内 `judge_data_requirement` SHALL 看到同一非空列表（允许引用相等或深拷贝等价）

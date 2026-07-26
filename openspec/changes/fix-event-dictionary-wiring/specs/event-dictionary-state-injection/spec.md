## ADDED Requirements

### Requirement: Clinic 路径注入事件字典
`/v1/clinic/stream`（及非流式若存在）在构建初始 State 时 SHALL 调用 `event_cache.get_event_dictionary()`，并将结果写入 `event_dictionary` 字段后进入 `clinic_graph`。

#### Scenario: clinic 请求进入 judge 时带有字典
- **WHEN** 事件字典拉取成功且非空，客户端调用 clinic stream
- **THEN** `judge_data_requirement` SHALL 读到非空 `event_dictionary`
- **AND** SHALL NOT 仅因未注入而打印「事件字典为空，使用默认数据需求」

### Requirement: 嵌套 clinic 透传事件字典
`call_clinic_agent` 构造 `clinic_state` 时 SHALL 包含 `event_dictionary`（优先使用意图 State 已有值，否则自行从 `event_cache` 获取）。

#### Scenario: conversation/suggest 进入嵌套 clinic
- **WHEN** 意图图路由到 `call_clinic_agent` 且缓存中有非空事件字典
- **THEN** 嵌套 `clinic_graph` 的 judge 节点 SHALL 看到非空 `event_dictionary`

### Requirement: Tip 路径在需要时注入
若 tip 执行路径包含依赖事件字典的节点（如 `judge_data_requirement`），tip 路由 SHALL 同样注入 `event_dictionary`；若 tip 图不依赖该字段，可省略但不得破坏现有 tip 行为。

#### Scenario: tip 图需要字典时已注入
- **WHEN** tip 图会执行 `judge_data_requirement`
- **THEN** 初始 State SHALL 含 `event_dictionary`

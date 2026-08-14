## Why

四张 LangGraph（intent / clinic / tip / care_alert）的 State 均为 TypedDict，路由与节点却普遍写成 `Dict[str, Any]`，靠字符串 key 塞值与 `.get`，可读性差、易静默丢字段。意图路径上 `intent_result` 仍是自由字典，编排中段同样难读。需在**不改变对外行为**的前提下，全仓统一为 Pydantic State，并收紧核心嵌套模型。

## What Changes

- 四图外层 State（`IntentState` / `ClinicState` / `TipState` / `CareAlertState`）由 TypedDict 改为 **Pydantic BaseModel**；路由/analyze 入口用构造函数赋值，禁止匿名 dict 堆字段作为主路径。
- 节点签名以对应 State 模型为准；读字段用属性；写回仍以**字段补丁 dict**（或模型 `model_dump` 子集）交给 LangGraph 合并，约定在 design 钉死。
- `shared` 跨图节点改为 **Protocol**（按所需字段组合），不再写死单一 State 类型。
- `stream_graph` / `node_thinking` 的终态合并改为对 Pydantic State 安全更新，MUST NOT 因未声明通道静默丢弃已注入字段。
- **核心 B**：引入 `IntentResult`、`DataRequirement` Pydantic 模型，替换图内 `intent_result` / `data_requirement` 的 `Dict[str, Any]` 主路径；care_alert `items` 使用既有 DTO 类型钉死。
- **非目标**：不改 CRUD/查记录/陪伴/护理留意的用户可见语义；不做全站所有嵌套袋全面模型化（如完整 QA 标量族可保持字段级）；不写测试文件。

## Capabilities

### New Capabilities

- `typed-graph-state`：全仓图 State 与核心嵌套结果的 Pydantic 契约、共享节点 Protocol、流式合并不得丢字段。

### Modified Capabilities

- `clinic-tip-event-dictionary-channel`：`ClinicState`/`TipState` 事件字典通道表述从 TypedDict 对齐为 Pydantic 字段，语义不变（仍须保留 `event_dictionary`）。
- `intent-state-field-alignment`：意图 State 字段对齐改为 Pydantic 模型字段；`intent_result` 主路径为 `IntentResult`。
- `langgraph-intent-graph`：图 State 类型为 Pydantic；入口构造与节点读写约定（行为路由不变）。

## Impact

- **代码**：`app/*/graphs/states/*`、四图节点与路由、`app/shared/graphs/**`、intent `classify`/`resolve_remark`/`pipeline`、clinic/tip/care_alert 数据准备链。
- **API**：请求/响应 JSON 契约不变；仅 Python 内部载体变化。
- **依赖**：沿用现有 Pydantic；无新外部服务。
- **风险**：合并漏字段、共享节点签名遗漏；靠四条主路径手工验收。

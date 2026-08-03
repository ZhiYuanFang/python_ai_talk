## ADDED Requirements

### Requirement: Single LangGraph orchestration for stream and non-stream

clinic、tip 与 intent 的数据准备（及 intent 冷启动图路径）SHALL 由同一已编译 LangGraph 图执行；流式与非流式 SHALL NOT 维护第二份平行的节点执行边表作为主路径。

#### Scenario: Clinic stream uses clinic_graph

- **WHEN** 客户端调用 `/v1/clinic/stream` 并进入数据准备
- **THEN** 系统 SHALL 通过 `clinic_graph` 的流式执行推进准备节点（含 needs_history 条件边）
- **AND** SHALL NOT 再以路由内手写 prepare_steps 列表作为准备编排主路径

#### Scenario: Non-stream intent still ainvoke

- **WHEN** 客户端调用非流式 intent 分析
- **THEN** 系统 SHALL 继续（或等价）使用 `intent_graph.ainvoke`，与流式共享同一图定义

#### Scenario: Tip stream uses tip_graph

- **WHEN** 客户端调用 `/v1/tip/stream` 并进入数据准备
- **THEN** 系统 SHALL 通过 `tip_graph`（或明确的同一图入口）执行准备，而非独立于图的步骤表主路径

### Requirement: Progressive thinking via graph custom stream

流式路径 SHALL 在每个将执行的编排节点之业务逻辑开始前，经 LangGraph custom 流（或等价节点内 stream writer）发出对应 thinking；SHALL NOT 仅依赖 `stream_mode=updates` 的节点完成事件作为该步 thinking 的触发。

#### Scenario: Thinking before slow node work

- **WHEN** 流式执行到达需调用 LLM 或外部 HTTP 的准备节点
- **THEN** 客户端 SHALL 在该节点业务 await 完成之前收到该节点 thinking SSE

#### Scenario: Thinking copy mapped by node name

- **WHEN** 图执行节点 `judge_needs_history`（或其它已映射节点）
- **THEN** thinking 内容 SHALL 来自既有节点名→文案映射（或与其等价的统一文案源）

#### Scenario: Ainvoke ignores custom

- **WHEN** 非流式路径 `ainvoke` 同一节点
- **THEN** 系统 SHALL 正常完成状态更新，且不要求产生 SSE thinking

### Requirement: SSE contract preserved

本能力 SHALL NOT 改变既有 SSE 事件类型约定（如 thinking / answer / done，以及 intent answer 的 JSON 包装方式）。

#### Scenario: Clinic thinking and answer types

- **WHEN** `/v1/clinic/stream` 运行
- **THEN** 逐步进度仍以 `type=thinking` 推送，回答仍以 `type=answer`（及既有 done）推送

### Requirement: Nested clinic progress visible on intent stream

当 intent 流式路径进入需执行 clinic 数据准备的分支时，系统 SHALL 使 clinic 准备阶段的逐步 thinking 对客户端可见（通过内层 astream 转发 custom，或等价的可观测流边界）。

#### Scenario: History or conversation via call_clinic_agent

- **WHEN** intent 冷启动流式路由至 clinic agent 且执行 clinic 准备节点
- **THEN** 客户端 SHALL 能收到准备阶段的逐步 thinking，而非仅在 clinic 整段 `ainvoke` 结束后才出现进度

### Requirement: Answer token streaming remains after orchestration

最终口语/回答的 token 级流式输出 SHALL 可在图编排完成（或到达生成边界）之后进行；本要求 SHALL NOT 强制将 token 生成实现为仅返回 dict 的图节点。

#### Scenario: Clinic answer after prepare graph

- **WHEN** clinic 准备图执行结束
- **THEN** 系统 MAY 继续使用既有 `stream_response`（或等价）推送 answer chunks，且准备阶段 thinking 已按节点发出

### Requirement: Needs-history gate stays graph-owned

喂养历史门禁与范围拉取的条件跳过语义 SHALL 仅由 `clinic_graph`（及共享节点）表达；流式路径 SHALL NOT 再复制一套独立的 needs_history 步进条件作为编排真相。

#### Scenario: Gate false skips fetch in stream

- **WHEN** `needs_history` 为 false 且未 force，且走 clinic 流式
- **THEN** 图 SHALL 跳过范围判断与 fetch_history（与非流式 ainvoke 相同）
- **AND** 客户端 SHALL NOT 收到仅属于已跳过 `fetch_history` 节点的 thinking

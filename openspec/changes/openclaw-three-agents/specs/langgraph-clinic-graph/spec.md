## REMOVED Requirements

### Requirement: Clinic graph uses LangGraph StateGraph
**Reason**: Clinic 编排改为 OpenClaw 就绪 Agent 运行时，废止 LangGraph clinic_graph 权威。
**Migration**: 见 `openclaw-three-agents`；`/v1/clinic` 与 `/v1/clinic/stream` 改为 Clinic Agent（只读 tool）。

## ADDED Requirements

### Requirement: Clinic 入口保留产品契约
系统 SHALL 继续提供 clinic 同步与流式产品入口（路径可与现网 `/v1/clinic`、`/v1/clinic/stream` 对齐），内部 MUST 使用非 LangGraph 的 Clinic Agent 运行时，且 MUST NOT 暴露历史写 tool。

#### Scenario: clinic stream 仍可用
- **WHEN** 客户端调用 clinic 流式入口
- **THEN** 系统 MUST 能返回思考/回答类流式事件（产品帧可与现网兼容）
- **AND** 实现 MUST NOT 以 `clinic_graph` StateGraph 为编排权威

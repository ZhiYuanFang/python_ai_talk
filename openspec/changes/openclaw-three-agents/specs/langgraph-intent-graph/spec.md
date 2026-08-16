## REMOVED Requirements

### Requirement: intent_graph 状态图结构
**Reason**: 编排改为 OpenClaw 就绪 Agent 运行时，废止 LangGraph StateGraph 作为意图编排权威。
**Migration**: 见 `openclaw-three-agents`；Intent 主路径改为 Agent+tool，不再构建 intent_graph。

### Requirement: IntentState 定义
**Reason**: 随 LangGraph intent_graph 一并废止。
**Migration**: 使用 Agent 运行时状态/会话模型；对外 IntentResponse 字段契约由 `intent-analysis` 等能力约束。

### Requirement: intent_graph 与路由集成
**Reason**: 路由不再调用 LangGraph invoke。
**Migration**: `/v1/analyze/intent` 改为调用 OpenClaw 就绪 Intent Agent 运行时。

### Requirement: intent_graph 兼容性
**Reason**: 图返回路径删除；对外兼容由产品 API 契约另行约束。
**Migration**: 保持 Intent 对外响应字段语义，实现不再经 intent_graph。

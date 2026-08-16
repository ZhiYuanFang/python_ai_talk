## MODIFIED Requirements

### Requirement: 编排不以 LangGraph 为权威
系统 SHALL 使用**真实 OpenClaw Gateway**编排 Intent/Clinic/Care Alert。系统 MUST NOT 再以 LangGraph `StateGraph` 或以 Python 进程内步骤表/迷你 agent loop 作为编排权威。`OPENCLAW_GATEWAY_URL`（或 Go 侧等价配置）MUST 指向实际 Gateway 并被调用。

#### Scenario: 禁止迷你 loop 冒充
- **WHEN** 代码仅含 `run_agent_steps` 类进程内编排且未调用 Gateway
- **THEN** 该实现 MUST NOT 被视为满足 OpenClaw 三 Agent 编排要求

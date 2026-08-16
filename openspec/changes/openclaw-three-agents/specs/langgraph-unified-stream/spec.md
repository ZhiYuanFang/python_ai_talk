## REMOVED Requirements

### Requirement: Single LangGraph orchestration for stream and non-stream
**Reason**: 废止 LangGraph 统一编排；tip 删除；clinic/intent 改 OpenClaw 就绪运行时。
**Migration**: 见 `openclaw-three-agents` 与 `retire-tip-agent`；流式与非流式共享同一 Agent 准备逻辑，但 MUST NOT 再以已编译 StateGraph 为权威。

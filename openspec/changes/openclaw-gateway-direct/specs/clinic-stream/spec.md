## REMOVED Requirements

### Requirement: Python /v1/clinic/stream 为陪伴流式权威入口
**Reason**: Clinic 改经 OpenClaw Gateway；Go 不再以 Python clinic stream 为编排上游。
**Migration**: Go 消费 Gateway Clinic agent 的流式/分块事件并映射到现有 WS/SSE 产品帧（若保留）。

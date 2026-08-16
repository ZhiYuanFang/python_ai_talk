## MODIFIED Requirements

### Requirement: 配置区分 Gateway 与飞轮与业务 API
系统配置 SHALL 区分：`OPENCLAW_GATEWAY_URL`（Go 调用的 Gateway）、业务 `GO_API_BASE_URL`/`HISTORY_SERVICE_URL`（tools 打历史）、`FLYWHEEL_BASE_URL`（仅飞轮 tool 服务/我方）。Go 业务配置 MUST NOT 包含飞轮基址作为必填依赖。Python MUST NOT 再作为意图/Clinic/Care 编排入口的默认上游。

#### Scenario: Go 配 Gateway
- **WHEN** 部署 voice/gateway 进程
- **THEN** MUST 能配置 OpenClaw Gateway 基址以发起 agent run
- **AND** MUST NOT 再依赖 `PYTHON_AI_TALK_URL` 作为 Intent/Clinic/Care 编排上游（可保留仅用于临时迁移期，正式验收 MUST 切断）

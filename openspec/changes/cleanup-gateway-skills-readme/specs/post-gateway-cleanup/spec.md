## ADDED Requirements

### Requirement: 删除无入口编排与 Care 飞轮残留

在 Gateway 已成为编排权威之后，Python 仓 MUST 删除：空 `agents` 包伪装、无 HTTP 入口的 Intent/Clinic 图编排与 `intent_pipeline`、Care 算卡与 Care 飞轮实现。系统 MUST 保留 `/v1/tools/*`、`/v1/knowledge/*`、`/v1/health` 及 Intent/Clinic 飞轮门面所需实现。

#### Scenario: 保留面

- **WHEN** 清理完成后启动 FastAPI
- **THEN** 路由 MUST 仍暴露 health、openclaw tools、knowledge
- **AND** `flywheel_facade` MUST 仍能 Intent retrieve/record 与 Clinic record（无 Care 飞轮 API）

#### Scenario: 禁止 Care 飞轮方法

- **WHEN** 清理完成
- **THEN** MUST NOT 存在可调用的 Care prompt/ledger 飞轮写入路径（含 facade 上的 care feedback 委托）

### Requirement: Go 与新 Python 面一致

Go 业务 Intent/Clinic/Care MUST 继续仅经 OpenClaw Gateway 编排。系统 MUST NOT 再从业务路径调用 Python `/v1/analyze|clinic|care-alert`。无调用方的 Python 编排客户端代码 MUST 删除或迁出，避免误导。部署清单 MUST 配置 `OPENCLAW_GATEWAY_URL`（及 token），不得将 `PYTHON_AI_TALK_URL` 表述为编排上游。

#### Scenario: 无编排调用 PythonAIClient

- **WHEN** 检索 go_ai_talk voice 业务调用链
- **THEN** Intent/Clinic/Care 成功路径 MUST 使用 OpenClaw HTTP 客户端
- **AND** MUST NOT 存在对 `PythonAIClientFromCfg` 的业务调用

#### Scenario: compose 配置对齐

- **WHEN** 查看 Go 微服务 compose / 配置示例
- **THEN** MUST 出现 `OPENCLAW_GATEWAY_URL`（或等价配置键）说明
- **AND** 若仍保留 `PYTHON_AI_TALK_URL`，注释 MUST 标明非 Intent/Clinic/Care 编排上游

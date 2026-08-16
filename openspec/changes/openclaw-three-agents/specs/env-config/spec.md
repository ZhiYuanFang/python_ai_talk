## ADDED Requirements

### Requirement: 生产 .env.prod 适配 OpenClaw 三 Agent
`env/.env.prod` SHALL 删除 Python 应用未使用或重构后无意义的变量（至少包括 `DEVICE_SERVICE_URL`、`VOICE_SERVICE_URL`，以及 tip/LangGraph 专用变量若存在）。SHALL 增加并赋值与重构对齐的变量：`GO_API_BASE_URL`、`HISTORY_SERVICE_URL`、`FLYWHEEL_BASE_URL`（可空表示进程内）、`HISTORY_READ_TOP_K_MAX`、Care Alert 飞轮相关 `CARE_ALERT_*`，以及可选 `OPENCLAW_GATEWAY_URL`。三层命名（`.env` / compose 注入 / `settings`）MUST 保持一致。

#### Scenario: 无用兄弟仓变量删除
- **WHEN** 审查生产 `env/.env.prod`
- **THEN** 文件 MUST NOT 再包含 `DEVICE_SERVICE_URL` 或 `VOICE_SERVICE_URL`

#### Scenario: 重构变量存在
- **WHEN** 审查生产 `env/.env.prod`
- **THEN** 文件 MUST 包含 `GO_API_BASE_URL` 与 `HISTORY_SERVICE_URL` 与 `HISTORY_READ_TOP_K_MAX`

### Requirement: 生产 Go 基址为胖宝域名
生产环境 `GO_API_BASE_URL` 与 `HISTORY_SERVICE_URL` SHALL 赋值为 `https://www.pangbao.cuplay.top`（无尾斜杠）。该值对应 Go/网关生产入口（见胖宝站点 https://www.pangbao.cuplay.top/）。

#### Scenario: prod 写入公网 Go 域名
- **WHEN** 应用生产 `env/.env.prod` 完成
- **THEN** `GO_API_BASE_URL` MUST 等于 `https://www.pangbao.cuplay.top`
- **AND** `HISTORY_SERVICE_URL` MUST 等于 `https://www.pangbao.cuplay.top`

### Requirement: 飞轮基址与业务基址分离
`FLYWHEEL_BASE_URL` SHALL 表示我方飞轮面（空=进程内）。业务 `GO_API_BASE_URL` / `HISTORY_SERVICE_URL` 可指向 Go 或客户 API；MUST NOT 用同一配置项覆盖飞轮使其指向客户自建飞轮后端。

#### Scenario: 业务指向 Go 公网不影响飞轮锁定
- **WHEN** `HISTORY_SERVICE_URL` 为 `https://www.pangbao.cuplay.top` 且 `FLYWHEEL_BASE_URL` 为空
- **THEN** 飞轮 MUST 使用进程内（或我方默认）实现
- **AND** MUST NOT 要求飞轮 HTTP 打到客户自有域名

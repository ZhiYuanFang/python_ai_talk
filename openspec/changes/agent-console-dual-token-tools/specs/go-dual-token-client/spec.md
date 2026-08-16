## ADDED Requirements

### Requirement: Go 分别配置 G 与 A

Go（或等价业务壳）SHALL 分别配置 Gateway 平台 Token（G）与 API Token（A）。调用智能体时 MUST 使用 G 通过门禁/Bearer；MUST 将 A 置于约定独立头（或等价）供插件转发 Python。本能力实现顺序 MUST 在本仓 Python 门禁与 tools 就绪之后（任务分期：先 Python，后 Go）。

#### Scenario: 分项配置存在

- **WHEN** Go 侧完成接入配置
- **THEN** 配置面 MUST 能独立设置 G 与 A（不同配置键）
- **AND** MUST NOT 仅用单一 token 同时充当 G 与 A

#### Scenario: 请求同时携带

- **WHEN** Go 发起智能体调用且需要 history CRUD
- **THEN** 请求 MUST 携带有效 G 与有效 A（按约定位置）
- **AND** G 失效时调用 MUST 失败于智能体准入
- **AND** 缺 A 时 MUST NOT 期望 history CRUD 成功

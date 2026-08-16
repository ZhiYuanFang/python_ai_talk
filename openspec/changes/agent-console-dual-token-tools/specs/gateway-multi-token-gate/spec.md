## ADDED Requirements

### Requirement: 多 G 门禁

系统 SHALL 支持多个有效的 G Token。对外调智能体的入口 MUST 校验 G 属于注册表且为生效状态；通过后 MUST 使用内部单一 Gateway 凭证调用本机（或受信）OpenClaw Gateway。产品语义上的「多 Gateway Token」MUST NOT 依赖 OpenClaw 原生多 token 配置作为唯一实现。

#### Scenario: 有效 G 进入 Gateway

- **WHEN** 调用方携带有效且生效的 G 请求智能体接口（经门禁）
- **THEN** 门禁 MUST 接受并转发至 Gateway
- **AND** 转发所用内部凭证 MUST NOT 暴露为客户持有的 G

#### Scenario: 无效 G

- **WHEN** 调用方携带未知或错误的 G
- **THEN** 门禁 MUST 拒绝
- **AND** MUST NOT 转发至 Gateway

### Requirement: A 与 G 分离传递

调智能体时，G MUST 用于门禁/Bearer（或门禁约定位置）；A MUST 通过独立约定头（或等价）传递，供 Gateway 插件转发至 Python tools。系统 MUST NOT 要求用 A 代替 G 通过门禁，也 MUST NOT 要求用 G 代替 A 解析落库 URL。

#### Scenario: 仅有 G 无 A

- **WHEN** 请求仅通过 G 门禁但未带有效 A，且 Agent 调用了 history CRUD tool
- **THEN** 该 tool MUST 失败（无 CRUD 能力）
- **AND** 门禁本身 MUST NOT 仅因缺 A 而拒绝「进入编排」（除非实现选择在门禁层强制 A；若强制则须在文档与本 Scenario 对齐——默认不强制）

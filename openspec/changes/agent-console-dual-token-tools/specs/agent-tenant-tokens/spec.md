## ADDED Requirements

### Requirement: G 与 A Token 强制一对一

系统 SHALL 将 Gateway 平台 Token（G）与 API/落库 Token（A）作为不同概念管理，并强制 **1:1** 绑定。G 决定是否有资格调用智能体；A 决定 tools 落库/读史上游路由。管理员成对签发时 MUST 同时产生并绑定一对 G 与 A。

#### Scenario: 成对签发

- **WHEN** 管理员为某用户名/客户备注签发接入凭证
- **THEN** 系统 MUST 生成一对 G 与 A 并建立唯一绑定
- **AND** MUST NOT 允许一张 G 绑定多张 A，或一张 A 绑定多张 G

### Requirement: G 生效与失效

系统 SHALL 支持将 G Token 设为生效或失效。失效的 G MUST 导致无法通过智能体调用门禁。

#### Scenario: G 失效拒调智能体

- **WHEN** 调用方使用已失效的 G 作为调智能体凭证
- **THEN** 门禁 MUST 拒绝该请求
- **AND** 调用方 MUST NOT 到达可用的 Agent 编排结果

### Requirement: 无 A 或未配置 URL 则 CRUD 不可用

在 G 有效的前提下，若请求缺少有效 A、A 已失效、或对应 tool 槽位未配置完整 URL，系统 MUST 使依赖上游的 history CRUD/读工具失败（返回明确错误），MUST NOT 回退到环境变量中的默认胖宝 Go 域名。

#### Scenario: 缺 A 时写史失败

- **WHEN** 智能体调用已到达 Python history 写 tool 且未提供有效 A
- **THEN** 该 tool MUST 失败并说明缺少 API Token（或等价）
- **AND** MUST NOT 使用默认业务上游 URL 完成写入

#### Scenario: 槽位未配置

- **WHEN** A 有效但某 tool 槽位无完整 URL
- **THEN** 该 tool MUST 失败
- **AND** 其它已配置槽位 MUST NOT 被强制全部禁用（除非产品另有全局开关）

### Requirement: 无默认业务上游环境域名

Python 应用配置 MUST NOT 将胖宝 Go（或任一客户）业务 API 域名作为产品默认上游。上游 URL MUST 来自该 A 绑定租户在库中的配置。

#### Scenario: 新部署无手配

- **WHEN** 新环境仅配置 DB/管理员种子且未在控制台配置任何 tool URL
- **THEN** history 类 tools MUST 因未配置而失败
- **AND** MUST NOT 隐式请求内置默认 Go 主机

### Requirement: 按 A 解析完整 URL

Python 执行 history/baby_profile 类 tool 时 SHALL 使用请求中的 A（经约定头或等价机制）解析租户，并使用该租户为该 tool 槽位配置的**完整 URL**（含域名）发起上游 HTTP。

#### Scenario: 不同 A 打不同主机

- **WHEN** 两个租户为同一槽位配置了不同完整 URL 且各自请求携带对应 A
- **THEN** 系统 MUST 分别请求各自配置的 URL

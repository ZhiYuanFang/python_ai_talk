## ADDED Requirements

### Requirement: 主页入口仅 Token

智能体管理后台主页 SHALL 提供通过 **G Token 或 A Token** 进入 API 管理页的能力。系统 MUST NOT 提供仅凭用户名进入 API 管理页的能力。主页右上角 SHALL 提供管理员入口，点击后提示输入管理员用户名与密码。

#### Scenario: Token 进入 API 页

- **WHEN** 用户在主页提交有效的 G 或 A
- **THEN** 系统 MUST 进入该 G↔A 对所对应的 API 管理页

#### Scenario: 拒绝用户名进入

- **WHEN** 用户仅提供用户名而无有效 G/A
- **THEN** 系统 MUST NOT 进入 API 管理页

#### Scenario: 管理员入口

- **WHEN** 用户点击主页右上角管理员入口并提交正确管理员账密
- **THEN** 系统 MUST 进入管理员界面

### Requirement: 管理员成对签发与 G 状态

管理员界面 SHALL 支持按用户名（或客户备注）成对生成 G 与 A，并支持复制；SHALL 支持将 G 设为生效或失效；SHALL 维护 G↔A 一对一关系（分发语义为 1:1，MUST NOT 一 G 多 A）。

#### Scenario: 成对生成可复制

- **WHEN** 管理员输入用户名并生成凭证
- **THEN** 系统 MUST 展示可复制的 G 与 A（生成时可见明文）
- **AND** 二者 MUST 已 1:1 绑定

#### Scenario: 切换 G 失效

- **WHEN** 管理员将某 G 设为失效
- **THEN** 该 G 对调智能体门禁 MUST 立即（或在短 TTL 缓存后）视为无效

### Requirement: API 管理页双 Token 与 Go 接入说明

API 管理页（用户可见）SHALL 同时展示该对的 G Token 与 A Token，并均支持复制。同页 SHALL 从 Go/业务壳视角说明如何接入智能体与如何配置（含 G/A 分工、请求头约定、G 失效与缺 A 的行为）。同页 SHALL 允许配置各 tool 槽位的完整 URL（含域名），并只读展示各接口入参/出参及是否必填（来自平台契约 Catalog）。

#### Scenario: 展示并复制 G 与 A

- **WHEN** 用户进入 API 管理页
- **THEN** 页面 MUST 展示 G 与 A
- **AND** 用户 MUST 能分别复制二者

#### Scenario: Go 视角说明书可见

- **WHEN** 用户打开 API 管理页
- **THEN** 页面 MUST 包含面向业务壳/Go 的接入与配置说明（用户可读，非仅管理员文档）

#### Scenario: 配置完整 URL 与契约

- **WHEN** 用户为某 tool 槽位保存含域名的完整 URL
- **THEN** 系统 MUST 持久化该配置供该 A 路由使用
- **AND** 页面 MUST 展示该槽位入参/出参/必填说明

### Requirement: 品牌与主题

管理后台界面 SHALL 以「AI喂养智能体」为品牌主识别，主色调为浅蓝色系，并包含宝宝主题的主视觉氛围；全平台（主页、API 页、管理员页）MUST 使用同一视觉语言。主页第一屏 MUST 以品牌与进入表单为主，避免堆砌无关营销卡片。

#### Scenario: 主页品牌可见

- **WHEN** 用户打开管理后台主页
- **THEN** 「AI喂养智能体」MUST 作为首屏主要品牌信号可见
- **AND** 主色调 MUST 可识别为浅蓝色系并配合宝宝主题视觉

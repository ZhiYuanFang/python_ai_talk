## ADDED Requirements

### Requirement: Intent 写 tool 绑定四单动词 REST
Intent Agent 的历史写入 SHALL 通过四个独立业务 REST（或等价 tool）：**create**、**update**、**delete**、**end**（结束计时/未闭合记录）。Intent 主路径 MUST NOT 再依赖 `POST .../event/batch` 完成落库。一句话多事件时，运行时 MUST 按多次单动词调用执行，且 MUST 先执行 end 再执行其余写操作（若同轮存在 end）。

#### Scenario: 单次创建走 create
- **WHEN** 意图确认后需新增一条非结束计时记录
- **THEN** 系统 MUST 调用 create（add）REST/tool
- **AND** MUST NOT 为此调用 event/batch

#### Scenario: 同轮先 end 后 create
- **WHEN** 同一确认轮次同时需要 end 与 create
- **THEN** 系统 MUST 先调用 end，再调用 create

### Requirement: 共享只读业务 tool 面
可 BYO 的最小只读业务面 SHALL 至少包括：事件字典（options）、历史筛选（filter，含备注与 top_k/limit）、宝宝画像（birthday/profile）。Clinic 与 Care Alert MUST 仅使用只读面；Intent 可读可写。

#### Scenario: Clinic 可拉史与画像
- **WHEN** Clinic 需要月龄与近期史
- **THEN** 系统 MUST 能经配置的 profile 与 filter/list tool 获取
- **AND** MUST NOT 调用写 tool

### Requirement: 业务 tool URL 可重绑
系统 SHALL 允许按环境/租户重绑业务 tool 的 base URL 与 path（对接自有 Go 或客户 API）。重绑 MUST NOT 影响飞轮锁定基址（见 `hosted-flywheel-aggregate`）。

#### Scenario: 重绑 create 指向客户 API
- **WHEN** 配置将 history.create 指向客户 HTTPS 端点且契约字段对齐
- **THEN** Intent 落库 MUST 调用该端点
- **AND** 飞轮写入 MUST 仍走我方飞轮面

## ADDED Requirements

### Requirement: README 文档化控制台上游 URL 填法

仓库根 `README.md` SHALL 在管理控制台相关章节中，为 Agent History / baby_profile tools 提供可抄填的上游配置说明，且 MUST 包含：（1）推荐上游基址为 Go **主网关**（gateway-service，典型 `:9701`）或直连 **history-service**（典型 `:9801`），MUST NOT 将 **gateway-app**（典型 `:9702`）表述为 Agent tools 默认上游；（2）控制台 Catalog 八槽位与 Go HTTP path 的对照表（至少覆盖 `history_create`→`/device/history/api/event/add`、`history_update`→`.../event/update`、`history_delete`→`.../event/delete`、`history_end_latest`→`.../event/end-latest`、`history_filter`→`.../filter`、`history_list`→`.../list`、`history_options`→`.../event/options`、`baby_profile`→`.../birthday`）；（3）说明对现网胖宝 history API，「上游 Bearer」MUST 留空（可选字段保留给真正需要 `Authorization: Bearer` 的其它上游），MUST NOT 要求填写终端用户日更 JWT。

#### Scenario: 运维按 README 配置控制台

- **WHEN** 运维打开 README 管理页章节并为某租户配置 tools 上游
- **THEN** 文档中存在以主网关或 history-service 为 BASE 的完整 URL 示例或 path 表
- **AND** 文档明确上游 Bearer 对现网 history 留空
- **AND** 文档明确勿将 gateway-app 作为 Agent tools 默认上游

### Requirement: 控制台页内说明与 README 上游指引一致

API 管理页展示的 Go/业务壳接入说明（服务端生成的 guide 文案）SHALL 与 README 中关于上游基址选择、八槽位 path、上游 Bearer 留空的语义一致，MUST NOT 仅提示「填完整 URL」而无 path 或基址约束。

#### Scenario: 租户打开 API 管理页

- **WHEN** 租户使用有效 G 或 A 进入 API 管理页
- **THEN** 页内 guide 含主网关/history 基址指引与 Catalog 对应 path（或等价完整 URL 表）
- **AND** guide 说明现网 history 上游 Bearer 留空

### Requirement: API 管理页 SHALL 渲染 guide 为 Markdown

API 管理页中「Go / 业务壳接入说明」区域 SHALL 将服务端返回的 Markdown guide **渲染为 HTML**（至少支持标题、列表、代码块与 GFM 表格），MUST NOT 以纯文本形式原样展示 `##`、`|` 等 Markdown 标记作为最终可读版式。实现 MUST 使用前端轻量 Markdown 库（本变更约定 vendoring `marked`），MUST NOT 依赖仅 CDN 且离线不可用的唯一加载方式作为正式路径。

#### Scenario: guide 含表格与标题时可见结构化排版

- **WHEN** 租户进入 API 管理页且 guide 含二级标题与 Markdown 表格
- **THEN** 页面中可见渲染后的标题与表格结构（非一整块未解析的 Markdown 源码）

### Requirement: Guide SHALL 说明能力、调用方式与完整 http URL

控制台 guide（`_go_guide_markdown` 或等价）SHALL 面向业务接入方说明：（1）本智能体能力概要（至少覆盖 intent / clinic / care_alert 三类 agent 的用途一句）；（2）外界如何调用门禁（G/A 头、`model`、`session-key`、勿直连裸 OpenClaw）；（3）参考 API MUST 以 **完整 URL** 写出（含 `http://` 或 `https://` 与主机占位或当前请求推导的公网/访问基址），至少包括门禁 chat completions、控制台入口，以及下方 tools 上游八槽位的完整示例 URL。MUST NOT 仅给出无主机的 path（如单独 `/agent-gate/...`）作为唯一参考。

#### Scenario: 接入方阅读 guide 可抄完整门禁 URL

- **WHEN** 租户打开 API 管理页查看接入说明
- **THEN** guide 中出现以 `http://` 或 `https://` 开头的门禁 chat completions 完整 URL
- **AND** guide 含 intent/clinic/care_alert 能力说明
- **AND** 上游 history 槽位示例亦为完整 URL（含主机占位或可解析基址）

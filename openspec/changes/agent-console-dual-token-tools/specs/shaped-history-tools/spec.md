## ADDED Requirements

### Requirement: History tools 经 Python 且出口为瘦结果

系统 SHALL 通过 Python `/v1/tools`（或等价前缀）暴露 history 读与写（至少含 create/update/delete/end_latest、filter、list、options、baby_profile）。OpenClaw 插件 MUST NOT 在产品路径上再直打 Go `/device/history/api/*`。读类工具返回给模型的内容 MUST 为瘦结构：历史事件 SHALL 裁剪约定字段并将时间转为 Asia/Shanghai 可读文案；`baby_profile` SHALL 提供推导后的月龄（及可选月龄带），MUST NOT 仅回传未解释的生日时间戳作为唯一月龄信息。

#### Scenario: 插件只打 toolsBaseUrl

- **WHEN** Gateway 插件执行任意 history 或 baby_profile tool
- **THEN** HTTP 目标 MUST 为配置的 `toolsBaseUrl` 下 Python tools 路径
- **AND** MUST NOT 使用 `historyBaseUrl` 直打业务 Go（该配置项 MUST 移除或文档标明废弃）

#### Scenario: baby_profile 含月龄

- **WHEN** 上游返回含可解析 birthday 的画像且 tool 成功
- **THEN** 回给模型的载荷 MUST 包含可用的 `ageMonths`（或等价字段）；未知生日则月龄为空/未知且 MUST NOT 编造

#### Scenario: history_filter 瘦字段

- **WHEN** `history_filter`（或等价）成功返回事件列表
- **THEN** 每条事件注入模型前 MUST 仅保留约定字段（如 eventName、eventNumber、startTime、endTime、remark 等）
- **AND** 时间字段 MUST 为可读中文而非原始 Unix 戳为主展示

### Requirement: 写工具短回执

写史工具成功时 SHALL 向模型返回短回执（如 ok 与 id），MUST NOT 将上游完整冗余响应整包作为唯一上下文。

#### Scenario: create 成功

- **WHEN** history_create（或等价）上游写入成功
- **THEN** tool 结果 MUST 包含成功语义与可用标识（若有）
- **AND** MUST NOT 依赖未裁剪的上游整包作为模型主输入

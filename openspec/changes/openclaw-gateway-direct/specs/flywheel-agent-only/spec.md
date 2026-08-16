## ADDED Requirements

### Requirement: Go 与飞轮零关系
`go_ai_talk` 业务代码与配置 SHALL NOT 调用、转发、存储或解析数据飞轮（intent/clinic/care）。飞轮基址 MUST NOT 出现在 Go 服务配置的业务必填项中。验收时对 Go 业务树检索飞轮调用 MUST 为空（允许历史 OpenSpec 文档提及，但实现路径不得存在）。

#### Scenario: 删除 Go 飞轮转发
- **WHEN** 检查 clinic feedback 与 care-alert feedback 控制器
- **THEN** MUST NOT 再存在将反馈 POST 到 Python 飞轮/反馈学习接口的实现
- **AND** Clinic 显式点赞 API MUST 删除或对客户端返回不存在/废弃且无飞轮副作用

### Requirement: 飞轮仅两仓且仅经 Gateway agent
数据飞轮 SHALL 仅包含 **Intent** 与 **Clinic** 两仓。写入/检索 SHALL 仅由对应 Gateway agent 经飞轮 tools 触发。Care Alert MUST NOT 拥有飞轮仓。

#### Scenario: Intent 写成功后可记录
- **WHEN** Intent agent 经写 tool 成功落库且策略要求学习
- **THEN** Intent agent MAY 调用飞轮 record tool
- **AND** 该调用 MUST NOT 由 Go 发起

#### Scenario: Clinic 仅隐式采纳
- **WHEN** Clinic agent 在回合内判定上轮建议被隐式采纳
- **THEN** Clinic agent MAY 调用 Clinic 飞轮 record tool
- **AND** 系统 MUST NOT 提供面向 App 的显式 thumbs up/down 飞轮入口

### Requirement: 前端不直打飞轮/Python 学习面
客户端 MUST NOT 直接请求 Python 飞轮或学习类 HTTP 接口。学习闭环 MUST 发生在 Gateway agent → 飞轮 tool 路径内。

#### Scenario: 无 App→Python 反馈
- **WHEN** 用户在 App 继续 Clinic 对话
- **THEN** 隐式采纳若发生 MUST 在 Gateway Clinic agent 路径内完成
- **AND** App MUST NOT 再调用 `/device/api/clinic/feedback` 作为飞轮写入手段

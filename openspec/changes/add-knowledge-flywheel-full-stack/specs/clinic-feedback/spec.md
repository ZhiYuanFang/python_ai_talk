## ADDED Requirements

### Requirement: 诊疗回答返回 answerId
系统 SHALL 在诊疗流式回答完成时，返回包含 answerId 的 done 事件。

#### Scenario: 诊疗回答完成返回 answerId
- **WHEN** 诊疗流式回答生成完成
- **THEN** 系统发送 `{"type": "done", "answerId": <id>}` 事件

### Requirement: 接收诊疗回答反馈
系统 SHALL 提供 `/v1/clinic/feedback` 接口，接收诊疗回答的用户反馈。

#### Scenario: 成功接收诊疗反馈（点赞）
- **WHEN** 用户对诊疗回答点赞，调用 `/v1/clinic/feedback`，feedback=1
- **THEN** 系统返回 200 状态码，相关知识的质量分提升

#### Scenario: 成功接收诊疗反馈（点踩）
- **WHEN** 用户对诊疗回答点踩，调用 `/v1/clinic/feedback`，feedback=-1
- **THEN** 系统返回 200 状态码，相关知识的质量分降低

#### Scenario: 无效的反馈值
- **WHEN** 用户提交 feedback 值不是 1 或 -1
- **THEN** 系统返回 400 状态码，提示无效的反馈值

### Requirement: 诊疗会话持久化存储
Go 服务 SHALL 将诊疗会话存储到 MySQL 数据库，包含问题、回答和反馈信息。

#### Scenario: 诊疗会话落库
- **WHEN** 诊疗回答生成完成
- **THEN** Go 服务将会话信息（question、answer）插入 clinic_session 表

#### Scenario: 反馈更新到数据库
- **WHEN** 用户提交诊疗反馈
- **THEN** Go 服务更新 clinic_session 表的 feedback 和 feedback_at 字段

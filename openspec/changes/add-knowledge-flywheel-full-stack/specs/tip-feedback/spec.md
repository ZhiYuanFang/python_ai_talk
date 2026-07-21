## ADDED Requirements

### Requirement: 接收小贴士反馈
系统 SHALL 提供 `/v1/tip/feedback` 接口，接收小贴士的用户反馈。

#### Scenario: 成功接收小贴士反馈（认同）
- **WHEN** 用户认同小贴士，调用 `/v1/tip/feedback`，feedback=1
- **THEN** 系统返回 200 状态码，相关知识的质量分提升

#### Scenario: 成功接收小贴士反馈（不认同）
- **WHEN** 用户不认同小贴士，调用 `/v1/tip/feedback`，feedback=-1
- **THEN** 系统返回 200 状态码，相关知识的质量分降低

#### Scenario: 无效的 tipId
- **WHEN** 用户提交不存在的 tipId
- **THEN** 系统返回 404 状态码，提示小贴士不存在

### Requirement: Go 侧反馈接口
Go 服务 SHALL 提供 `/tip/feedback` 接口，接收 Flutter 客户端的小贴士反馈，并同步到 Python 服务。

#### Scenario: Flutter 提交小贴士反馈
- **WHEN** Flutter 客户端调用 Go 的 `/tip/feedback` 接口
- **THEN** Go 服务将反馈写入数据库，并调用 Python 的 `/v1/tip/feedback` 接口

### Requirement: 反馈频率限制
系统 SHALL 对同一用户（device_no）的反馈频率进行限制，5 分钟内最多提交 3 次反馈。

#### Scenario: 正常频率反馈
- **WHEN** 用户在 5 分钟内提交第 3 次反馈
- **THEN** 系统正常处理反馈

#### Scenario: 超过频率限制
- **WHEN** 用户在 5 分钟内提交第 4 次反馈
- **THEN** 系统返回 429 状态码，提示频率限制

## ADDED Requirements

### Requirement: 胖宝诊疗流式接口
系统 SHALL 提供 `/v1/clinic/stream` HTTP POST 接口，支持 SSE 流式响应，接收诊疗问题和设备编号，返回流式诊疗建议。

#### Scenario: 成功返回流式诊疗结果
- **WHEN** 客户端发送 POST 请求到 `/v1/clinic/stream`，body 包含 `{"question": "宝宝最近有点拉肚子", "deviceNo": "test123", "model": {"provider": "deepseek", "name": "deepseek-chat", "maxInFlight": 3}}`
- **THEN** 服务返回 HTTP 200，Content-Type 为 `text/event-stream`，流式返回包含 thinking 和 answer 的 JSON 对象

#### Scenario: 流式响应格式
- **WHEN** 服务返回流式响应
- **THEN** 每个 SSE 事件包含 `{"type": "thinking", "content": "..."}` 或 `{"type": "answer", "content": "..."}`

#### Scenario: 失败 - 缺少必要参数
- **WHEN** 客户端发送 POST 请求到 `/v1/clinic/stream`，body 缺少 `question` 或 `deviceNo` 字段
- **THEN** 服务返回 HTTP 400，响应 body 包含错误信息

### Requirement: 向量检索增强诊疗
系统 SHALL 在胖宝诊疗场景中使用向量检索增强 LLM 回答，从 Chroma 向量库中检索相关母婴知识。

#### Scenario: 检索相关知识
- **WHEN** 用户提问"宝宝拉肚子怎么办"
- **THEN** 系统从向量库中检索与"拉肚子"相关的母婴知识，并作为 context 传递给 LLM

#### Scenario: 无相关知识
- **WHEN** 用户提问的问题在向量库中无匹配知识
- **THEN** 系统仅使用历史数据和宝宝画像作为 context

### Requirement: 历史数据获取
系统 SHALL 根据用户提问智能判断需要拉取的历史数据范围，并从 history-service 获取。

#### Scenario: 获取近期喂养记录
- **WHEN** 用户提问"宝宝最近食欲不好"
- **THEN** 系统拉取最近 7 天的喂养记录

#### Scenario: 获取特定时间段记录
- **WHEN** 用户提问"昨天宝宝吃了什么"
- **THEN** 系统拉取昨天的喂养记录

### Requirement: 宝宝画像获取
系统 SHALL 从 device-service 获取宝宝的生日信息。

#### Scenario: 成功获取宝宝画像
- **WHEN** 服务收到诊疗请求
- **THEN** 系统从 device-service 获取宝宝生日信息，计算宝宝年龄

#### Scenario: 获取宝宝画像失败
- **WHEN** 从 device-service 获取宝宝画像失败
- **THEN** 系统继续处理请求，但不使用宝宝年龄信息
## ADDED Requirements

### Requirement: 意图分析接口
系统 SHALL 提供 `/v1/analyze/intent` HTTP POST 接口，接收自然语言文本和设备编号，返回结构化意图分析结果。

#### Scenario: 成功识别喂养开始意图
- **WHEN** 客户端发送 POST 请求到 `/v1/analyze/intent`，body 包含 `{"text": "开始喂奶", "deviceNo": "test123", "model": {"provider": "deepseek", "name": "deepseek-chat", "maxInFlight": 3}}`
- **THEN** 服务返回 HTTP 200，响应 body 包含 `{"target_type": "feeding", "action": "start", "event_name": "哺乳", "keywords": ["喂奶"], "content": "开始哺乳记录"}`

#### Scenario: 成功识别喂养结束意图
- **WHEN** 客户端发送 POST 请求到 `/v1/analyze/intent`，body 包含 `{"text": "结束喂奶", "deviceNo": "test123", "model": {"provider": "deepseek", "name": "deepseek-chat", "maxInFlight": 3}}`
- **THEN** 服务返回 HTTP 200，响应 body 包含 `{"target_type": "feeding", "action": "end", "event_name": "哺乳", "keywords": ["喂奶"], "content": "结束哺乳记录"}`

#### Scenario: 成功识别单次喂养记录意图
- **WHEN** 客户端发送 POST 请求到 `/v1/analyze/intent`，body 包含 `{"text": "刚才喝了120ml奶粉", "deviceNo": "test123", "model": {"provider": "deepseek", "name": "deepseek-chat", "maxInFlight": 3}}`
- **THEN** 服务返回 HTTP 200，响应 body 包含 `{"target_type": "feeding", "action": "one", "event_name": "奶粉喂养", "keywords": ["喝了", "120ml", "奶粉"], "content": "记录奶粉喂养120ml"}`

#### Scenario: 成功识别历史查询意图
- **WHEN** 客户端发送 POST 请求到 `/v1/analyze/intent`，body 包含 `{"text": "今天吃了多少", "deviceNo": "test123", "model": {"provider": "deepseek", "name": "deepseek-chat", "maxInFlight": 3}}`
- **THEN** 服务返回 HTTP 200，响应 body 包含 `{"target_type": "history", "action": "search", "event_name": "", "keywords": ["今天", "吃了多少"], "content": ""}`

#### Scenario: 成功识别成长建议意图
- **WHEN** 客户端发送 POST 请求到 `/v1/analyze/intent`，body 包含 `{"text": "宝宝最近食量怎么样", "deviceNo": "test123", "model": {"provider": "deepseek", "name": "deepseek-chat", "maxInFlight": 3}}`
- **THEN** 服务返回 HTTP 200，响应 body 包含 `{"target_type": "suggest", "action": "suggestion", "event_name": "", "keywords": ["最近", "食量"], "content": ""}`

#### Scenario: 成功识别对话意图
- **WHEN** 客户端发送 POST 请求到 `/v1/analyze/intent`，body 包含 `{"text": "你好", "deviceNo": "test123", "model": {"provider": "deepseek", "name": "deepseek-chat", "maxInFlight": 3}}`
- **THEN** 服务返回 HTTP 200，响应 body 包含 `{"target_type": "conversation", "action": "reply", "event_name": "", "keywords": ["你好"], "content": "您好！我是您的母婴喂养助手，请问有什么可以帮您的？"}`

#### Scenario: 成功识别退出意图
- **WHEN** 客户端发送 POST 请求到 `/v1/analyze/intent`，body 包含 `{"text": "退出", "deviceNo": "test123", "model": {"provider": "deepseek", "name": "deepseek-chat", "maxInFlight": 3}}`
- **THEN** 服务返回 HTTP 200，响应 body 包含 `{"target_type": "exit", "action": "exit", "event_name": "", "keywords": ["退出"], "content": ""}`

#### Scenario: 失败 - 缺少必要参数
- **WHEN** 客户端发送 POST 请求到 `/v1/analyze/intent`，body 缺少 `text` 或 `deviceNo` 字段
- **THEN** 服务返回 HTTP 400，响应 body 包含错误信息

#### Scenario: 失败 - LLM 调用超时
- **WHEN** 客户端发送 POST 请求到 `/v1/analyze/intent`，LLM 调用超过超时时间
- **THEN** 服务返回 HTTP 504，响应 body 包含超时错误信息

### Requirement: 智能历史数据范围判断
系统 SHALL 根据用户输入的自然语言智能判断需要拉取的历史数据范围，而非固定时间段。

#### Scenario: 判断"今天"范围
- **WHEN** 用户输入"今天吃了多少"
- **THEN** 系统判断需要拉取最近 24 小时的历史数据

#### Scenario: 判断"最近一周"范围
- **WHEN** 用户输入"最近一周的喂养情况"
- **THEN** 系统判断需要拉取最近 7 天的历史数据

#### Scenario: 判断"上次"范围
- **WHEN** 用户输入"上次喂奶是什么时候"
- **THEN** 系统判断需要拉取最近 1 条喂养记录

#### Scenario: 判断"昨天"范围
- **WHEN** 用户输入"昨天喝了多少奶粉"
- **THEN** 系统判断需要拉取昨天 00:00-24:00 的历史数据

### Requirement: 事件字典缓存
系统 SHALL 缓存事件字典列表，缓存 TTL 为 24 小时。

#### Scenario: 首次请求缓存事件字典
- **WHEN** 服务启动后首次收到意图分析请求
- **THEN** 系统从 history-service 获取事件字典并缓存

#### Scenario: 缓存命中
- **WHEN** 服务在缓存有效期内收到意图分析请求
- **THEN** 系统直接使用缓存的事件字典

#### Scenario: 缓存失效重新获取
- **WHEN** 服务在缓存过期后收到意图分析请求
- **THEN** 系统重新从 history-service 获取事件字典并更新缓存
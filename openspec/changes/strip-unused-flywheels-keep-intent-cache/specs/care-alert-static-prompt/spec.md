## ADDED Requirements

### Requirement: Care-alert analyze uses static prompt only

护理留意分析 SHALL 使用静态 system/prompt 模板（例如本地 `prompt.json` 的 `output_format` 或等价内联文案）结合运行时注入的月龄与历史摘要生成留意项。系统 MUST NOT 根据用户反馈重写对比样例块，MUST NOT 维护 care_alert 反馈 ledger 或 suggestion→快照飞轮映射作为产品闭环。

#### Scenario: Analyze without flywheel rewrite

- **WHEN** 调用 `POST /v1/care-alert/analyze`（或流式等价）
- **THEN** 系统完成分析且不依赖对比样例飞轮重写结果

### Requirement: Care-alert feedback endpoint removed

系统 MUST NOT 提供 `POST /v1/care-alert/feedback`。对该路径的请求 SHALL 不由本服务作为飞轮 ACK 处理（路由不存在，由框架返回 404 或未挂载）。

#### Scenario: Feedback route absent

- **WHEN** 客户端请求 `POST /v1/care-alert/feedback`
- **THEN** 本服务 MUST NOT 执行 ledger 写入或 prompt 重写，且 MUST NOT 将该路径注册为有效业务路由

## ADDED Requirements

### Requirement: 用户输入字段对齐
向量匹配与意图分类节点 SHALL 从 State 读取 `user_input` 作为用户自然语言文本，不得仅依赖不存在的 `text` 字段导致空输入。

#### Scenario: 路由注入的文本可被向量节点使用
- **WHEN** 路由将 `user_input` 写入初始 State 且未写入 `text`
- **THEN** `match_event_by_vector` SHALL 使用该 `user_input` 执行检索

#### Scenario: 路由注入的文本可被分类节点使用
- **WHEN** 路由将 `user_input` 写入初始 State 且未写入 `text`
- **THEN** `classify_intent` SHALL 使用该 `user_input` 构建 LLM 消息

### Requirement: 模型配置字段对齐
意图分类（及依赖模型配置的意图节点）SHALL 从 State 读取 `model_config`，不得仅依赖不存在的 `model` 字段导致错误默认模型 silently 生效而不读路由配置。

#### Scenario: 路由模型配置生效
- **WHEN** 路由写入 `model_config.provider` 与 `model_config.name`
- **THEN** `classify_intent` 创建 LLM 客户端时 SHALL 使用上述配置

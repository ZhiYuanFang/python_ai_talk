## MODIFIED Requirements

### Requirement: 用户输入字段对齐
向量匹配与意图分类节点 SHALL 从 Pydantic 意图 State 读取 `user_input` 作为用户自然语言文本，不得仅依赖不存在的 `text` 字段导致空输入。

#### Scenario: 路由注入的文本可被向量节点使用
- **WHEN** 路由将 `user_input` 写入初始 State 且未写入 `text`
- **THEN** 若仍存在事件名向量匹配节点，SHALL 使用该 `user_input` 执行检索；若不存在该节点，本场景不适用但分类节点场景仍生效

#### Scenario: 路由注入的文本可被分类节点使用
- **WHEN** 路由将 `user_input` 写入初始 State 且未写入 `text`
- **THEN** `classify_intent` SHALL 使用该 `user_input` 构建 LLM 消息

### Requirement: 模型配置字段对齐
意图分类（及依赖模型配置的意图节点）SHALL 从 Pydantic 意图 State 读取 `model_config`，不得仅依赖不存在的 `model` 字段导致错误默认模型 silently 生效而不读路由配置。

#### Scenario: 路由模型配置生效
- **WHEN** 路由写入 `model_config.provider` 与 `model_config.name`
- **THEN** `classify_intent` 创建 LLM 客户端时 SHALL 使用上述配置

## ADDED Requirements

### Requirement: 意图结果主路径为 IntentResult
意图图在分类、备注反查与确认相关管线中 SHALL 将意图结果存为 Pydantic `IntentResult`（名称以实现为准），MUST NOT 以无模式字典作为主路径唯一载体。

#### Scenario: 分类后 State 含 IntentResult
- **WHEN** `classify_intent` 成功
- **THEN** State 上的意图结果 SHALL 暴露 `op`、`event_name`、`event_id` 等字段供后续节点属性或等价访问
- **AND** 备注反查节点 SHALL 能更新该结果上的 `event_id` / `remark_keyword` 而不退回无模式 dict 主存储

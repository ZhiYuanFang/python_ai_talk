## ADDED Requirements

### Requirement: Inject at most one high-scoring knowledge item
系统在将向量检索结果写入供 tip/clinic（及共用 search_vectors 的路径）生成用的 `knowledge` 时，SHALL 最多保留相似度最高的 1 条（K=1）。

#### Scenario: Multiple hits keep only top score
- **WHEN** 向量检索返回多条结果且最高分不低于门槛
- **THEN** State 中用于生成的 `knowledge` 列表长度 SHALL 为 1，且为相似度最高的那一条

### Requirement: Drop knowledge below score threshold 0.6
系统 SHALL 使用可配置的最小相似度门槛，默认值为 0.6；当最高分结果的 score 低于该门槛时，SHALL 将用于生成的 `knowledge` 置为空列表，并仍允许口语化陪伴回答。

#### Scenario: Low top score yields empty knowledge
- **WHEN** 最高分结果的 score 小于 0.6（或当前配置的门槛）
- **THEN** 生成提示词中的「可参考的知识」块 SHALL 不包含任何知识条目（knowledge 为空）

#### Scenario: High enough top score is injected
- **WHEN** 最高分结果的 score 大于或等于 0.6（或当前配置的门槛）
- **THEN** 该条知识 SHALL 出现在生成用的 knowledge 中

### Requirement: Companion dialogue window is three turns
系统 SHALL 将按 `device_no` 的陪伴会话最多保留最近 3 轮 user+assistant 对话（默认配置），截断与注入 `chat_context` 均遵守该上限。

#### Scenario: Fourth turn drops the oldest
- **WHEN** 会话已有 3 轮且再次成功追加 1 轮
- **THEN** 会话中仅保留最新的 3 轮

### Requirement: Flywheel knowledge ids match injected knowledge
系统在 tip/clinic 将会话 `last_suggestion.knowledge_ids` 写为与本轮用于生成的 `knowledge` 文档 id 一致；当 knowledge 为空时，knowledge_ids SHALL 为空。

#### Scenario: No knowledge means empty flywheel ids
- **WHEN** 本轮因分数门槛未注入任何知识并完成 tip 或 clinic 回答写入会话
- **THEN** 该轮 last_suggestion 的 knowledge_ids SHALL 为空列表

### Requirement: Feeding history volume unchanged by this change
本能力 SHALL NOT 要求修改喂养 `history_events` 写入提示词的条数上限逻辑。

#### Scenario: Feeding history slicing stays as before
- **WHEN** clinic 或 tip 构建含喂养记录的用户消息
- **THEN** 喂养记录条数截取规则不因本 change 被要求改为 3 条对话窗逻辑

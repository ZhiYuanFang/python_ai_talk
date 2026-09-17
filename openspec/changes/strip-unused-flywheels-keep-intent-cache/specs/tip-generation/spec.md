## ADDED Requirements

### Requirement: Tip generation without general knowledge

tip 开场生成 MUST NOT 检索或注入 `mother_baby_knowledge` 通识摘录。回答依据事件名、可选喂养史摘要、宝宝画像/月龄与提示词即可。

#### Scenario: Tip stream without search_vectors

- **WHEN** 调用 tip 流式开场
- **THEN** 执行路径 MUST NOT 进入通识向量检索节点，且 prompt MUST NOT 依赖「知识库参考」块

## ADDED Requirements

### Requirement: 意图分类 LLM 失败用户文案
当意图分类调用 LLM 失败（含缺 model、上游错误）时，系统 MUST NOT 假装完成有效 CRUD/查记录意图。系统 SHALL 向用户反馈固定文案「脑电波过载，请稍后重试」（可通过 `intent_result.content` 与/或流式 `thinking` 事件）。系统 MUST NOT 为该失败自动切换其它 LLM 模型后再继续分类。

#### Scenario: 分类失败软回执
- **WHEN** `classify_intent` 因 LLM 调用失败进入错误处理
- **THEN** 返回结果中用户可见文案 SHALL 为「脑电波过载，请稍后重试」
- **AND** SHALL NOT 继续尝试保底列表中的其它模型

#### Scenario: 流式分类失败可推 thinking
- **WHEN** 意图流式请求中分类 LLM 失败且存在 custom thinking 消费者
- **THEN** 系统 MAY 再推送一条内容为「脑电波过载，请稍后重试」的 thinking
- **AND** 最终 answer 中的用户可见说明 SHALL 含同一文案（或等价唯一告知）

## MODIFIED Requirements

### Requirement: 意图分析接口实现方式
意图分析接口 `/v1/analyze/intent` SHALL 使用 LangGraph StateGraph 编排替代手写 if/else 逻辑，并增加 history/suggest 意图的后处理能力。

#### Scenario: 使用 LangGraph 编排
- **WHEN** 接收到意图分析请求
- **THEN** 系统 SHALL 调用 intent_graph 执行意图分析流程
- **AND** 不 SHALL 使用手写 if/else 逻辑处理意图分类后的分支

#### Scenario: history 意图后处理
- **WHEN** 用户输入"今天喝了多少奶粉"，意图分析结果为 target_type=history, action=search
- **THEN** 系统 SHALL 调用 LLM 判断需要的 eventId 和时间范围
- **AND** 调用 Go 侧 filter API 拉取对应历史记录
- **AND** 调用 LLM 将历史记录总结为自然语言回答
- **AND** 将回答内容填充到 IntentResponse 的 content 字段

#### Scenario: suggest 意图后处理
- **WHEN** 用户输入"宝宝最近食量怎么样"，意图分析结果为 target_type=suggest, action=suggestion
- **THEN** 系统 SHALL 调用 LLM 判断需要的 eventId 和时间范围
- **AND** 调用 Go 侧 filter API 拉取对应历史记录
- **AND** 调用向量库检索相关知识
- **AND** 调用 Go 侧获取宝宝画像
- **AND** 调用 LLM 结合历史记录、知识和宝宝画像生成个性化建议
- **AND** 将建议内容填充到 IntentResponse 的 content 字段

#### Scenario: feeding 意图保持不变
- **WHEN** 意图分析结果为 target_type=feeding
- **THEN** 系统 SHALL 直接返回 IntentResponse，不进行后处理
- **AND** 不调用 LLM 判断数据需求

#### Scenario: conversation 意图保持不变
- **WHEN** 意图分析结果为 target_type=conversation
- **THEN** 系统 SHALL 使用预设的兜底文案作为 content
- **AND** 不调用 LLM 判断数据需求

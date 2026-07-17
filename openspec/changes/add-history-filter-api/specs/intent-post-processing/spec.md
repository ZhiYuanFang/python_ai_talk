## ADDED Requirements

### Requirement: history 意图后处理
当意图分析结果为 history（历史查询）时，系统 SHALL 调用 LLM 判断数据需求，拉取对应历史记录，并生成自然语言回答。

#### Scenario: 查询今天的奶粉喂养量
- **WHEN** 用户输入"今天喝了多少奶粉"，意图分析结果为 target_type=history, action=search
- **THEN** 系统 SHALL 调用 LLM 判断需要 eventId 对应的事件类型和"today"时间范围
- **AND** 调用 go 侧 filter API 拉取今天的奶粉喂养记录
- **AND** 调用 LLM 将历史记录总结为自然语言回答
- **AND** 将回答内容填充到 IntentResponse 的 content 字段

#### Scenario: 查询最近一周的母乳喂次数
- **WHEN** 用户输入"最近喂了几次母乳"，意图分析结果为 target_type=history, action=search
- **THEN** 系统 SHALL 调用 LLM 判断需要 eventId 对应的母乳喂养事件和"last_7_days"时间范围
- **AND** 调用 go 侧 filter API 拉取最近一周的母乳喂养记录
- **AND** 调用 LLM 将历史记录总结为自然语言回答

#### Scenario: 查询上次喂奶时间
- **WHEN** 用户输入"上次喂奶是什么时候"，意图分析结果为 target_type=history, action=search
- **THEN** 系统 SHALL 调用 LLM 判断需要所有喂养事件的 eventIds 和"last_1"时间范围
- **AND** 调用 go 侧 filter API 拉取最近一条喂养记录
- **AND** 调用 LLM 将记录格式化为自然语言回答

### Requirement: suggest 意图后处理
当意图分析结果为 suggest（成长建议）时，系统 SHALL 调用 LLM 判断数据需求，拉取历史记录、检索向量库知识、获取宝宝画像，并生成个性化建议。

#### Scenario: 分析宝宝最近食量
- **WHEN** 用户输入"宝宝最近食量怎么样"，意图分析结果为 target_type=suggest, action=suggestion
- **THEN** 系统 SHALL 调用 LLM 判断需要所有喂养事件的 eventIds 和"last_7_days"时间范围
- **AND** 调用 go 侧 filter API 拉取最近一周的喂养记录
- **AND** 调用向量库检索"宝宝食量"相关知识
- **AND** 调用 go 侧获取宝宝画像（生日、性别）
- **AND** 调用 LLM 结合历史记录、知识和宝宝画像生成个性化建议
- **AND** 将建议内容填充到 IntentResponse 的 content 字段

#### Scenario: 分析宝宝睡眠情况
- **WHEN** 用户输入"宝宝最近睡得好吗"，意图分析结果为 target_type=suggest, action=suggestion
- **THEN** 系统 SHALL 调用 LLM 判断需要"睡觉"事件对应的 eventId 和"last_7_days"时间范围
- **AND** 调用 go 侧 filter API 拉取最近一周的睡眠记录
- **AND** 调用向量库检索"宝宝睡眠"相关知识
- **AND** 调用 go 侧获取宝宝画像
- **AND** 调用 LLM 生成个性化建议

### Requirement: feeding 意图保持不变
当意图分析结果为 feeding（喂养记录）时，系统 SHALL 直接返回，不进行后处理。

#### Scenario: 开始喂养记录
- **WHEN** 用户输入"开始喂奶"，意图分析结果为 target_type=feeding, action=start
- **THEN** 系统 SHALL 直接返回 IntentResponse，不调用 LLM 判断数据需求
- **AND** 不调用 go 侧 filter API

#### Scenario: 结束喂养记录
- **WHEN** 用户输入"结束喂奶"，意图分析结果为 target_type=feeding, action=end
- **THEN** 系统 SHALL 直接返回 IntentResponse，不进行后处理

### Requirement: conversation 意图保持不变
当意图分析结果为 conversation（对话）时，系统 SHALL 使用兜底文案，不进行后处理。

#### Scenario: 闲聊对话
- **WHEN** 用户输入"你好"，意图分析结果为 target_type=conversation, action=reply
- **THEN** 系统 SHALL 使用预设的兜底文案作为 content
- **AND** 不调用 LLM 判断数据需求
- **AND** 不调用 go 侧 filter API

### Requirement: LLM 数据需求判断失败时的 fallback
当 LLM 判断数据需求失败（如返回格式错误）时，系统 SHALL 使用默认配置。

#### Scenario: LLM 返回格式错误
- **WHEN** 调用 LLM 判断数据需求，返回的 JSON 格式无效
- **THEN** 系统 SHALL 使用默认配置：事件ID为空（拉取所有）、时间范围为最近 7 天

#### Scenario: LLM 返回未知的时间范围
- **WHEN** 调用 LLM 判断数据需求，返回的 time_range 不在可选值列表中
- **THEN** 系统 SHALL 使用默认时间范围：最近 7 天

#### Scenario: LLM 返回不存在的事件ID
- **WHEN** 调用 LLM 判断数据需求，返回的 event_ids 不在事件字典中
- **THEN** 系统 SHALL 忽略该事件ID，使用空列表（拉取所有类型）

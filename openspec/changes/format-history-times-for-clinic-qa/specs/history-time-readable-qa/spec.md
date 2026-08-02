## ADDED Requirements

### Requirement: History timestamps are human-readable before LLM

系统在将喂养历史注入 LLM 提示之前，SHALL 把 `startTime`/`endTime` 从 Unix 时间戳转换为 Asia/Shanghai 时区的中文可读时间；SHALL 自动区分秒与毫秒时间戳。

#### Scenario: Point-query relative format within one hour

- **WHEN** 记录时间距现在不足 1 小时且采用点查/相对样式
- **THEN** 注入文本 SHALL 使用「刚刚」或「N分钟前」形式，而非原始时间戳数字

#### Scenario: Point-query minimal calendar beyond one day

- **WHEN** 记录时间距现在超过 1 天且与当前同属一年
- **THEN** 可读时间 SHALL 包含月日与时分，且不必包含年份

#### Scenario: Cross-year includes year

- **WHEN** 记录年份与当前年份不同
- **THEN** 可读时间 SHALL 包含年份

### Requirement: Latest history window is used for prompts

向 LLM 注入历史时，系统 SHALL 使用按时间从新到旧排列后的最近 N 条（或等价「最新窗口」），SHALL NOT 在倒序列表上误取最旧的尾部片段作为「最近记录」。

#### Scenario: Newest events preferred

- **WHEN** 历史列表含超过 N 条且已按时间倒序
- **THEN** 注入的窗口 SHALL 包含最新的记录而非最旧的 N 条

### Requirement: Summary questions use history over a time window

对「最近 N 天 / 总结 / 变化」类喂养汇总问题，系统 SHALL 将其视为查记录路径（非 feeding 直接落库），拉取对应时间窗与相关事件记录，并要求生成回答基于这些记录描述变化（如次数或总量趋势）；信息不足时 SHALL 明确说明。

#### Scenario: Seven-day milk summary is not feeding

- **WHEN** 用户输入类似「总结最近7天孩子的吃奶变化」
- **THEN** 向量/门禁路径 SHALL NOT 将其作为直接 feeding 落库；后续 SHALL 走查记录/clinic 答题路径

#### Scenario: Summary answer cites record-based trend

- **WHEN** 最近 7 天存在吃奶相关记录且用户要求总结变化
- **THEN** 回答 SHALL 体现基于记录的次数或量级信息（或明确数据不足），禁止完全脱离记录的空泛总结

### Requirement: Point-query answers must state readable start time

对询问「上次/什么时候开始」类问题，clinic 生成提示 SHALL 要求模型直接使用注入的可读开始时间作答，SHALL NOT 仅使用模糊时间表述。

#### Scenario: Last sleep start uses formatted time

- **WHEN** 用户问上一次睡眠何时开始且历史中有带 startTime 的睡眠记录
- **THEN** 回答 SHALL 包含与注入可读时间一致的具体时间信息

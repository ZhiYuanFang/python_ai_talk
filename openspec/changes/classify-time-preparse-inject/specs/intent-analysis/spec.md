## ADDED Requirements

### Requirement: 分类前注入规则预解析时间
当走意图分类 LLM 路径时，系统 SHALL 在构建分类 system 提示前，用规则从用户原文抽取钟点与时长（复用既有 clock/duration 抽取），并将结果以简短块注入提示（与进行中计时摘要一并出现于动态 extra）。注入内容 MUST 至少在可解析时包含：匹配原文片段、对应 Unix 秒（Asia/Shanghai）、可选时长秒数；若判定为半命中（有 clock 仍有未消费日/段残留），MUST 标明 partial/不完整，且 MUST NOT 要求模型采用残缺单点作为唯一权威。注入为软参考：模型可参考填写 `start_time`/`end_time`，最终时间权威由确认前规则覆盖（见用户确认相关能力）。无规则钟点时，注入 MUST 明示无预解析钟点，MUST NOT 编造钟点。

#### Scenario: 昨晚六点预解析进入分类提示
- **WHEN** 用户原文含可规则解析的「昨晚6点」（或语义等价）
- **AND** 系统构建 classify system 提示
- **THEN** extra（或等价动态段）SHALL 含该钟点的预解析 unix（对应昨日 18:00 Asia/Shanghai 或语义等价）
- **AND** SHALL 含可关联的原文片段（如「昨晚6点」）

#### Scenario: 半命中预解析标明不完整
- **WHEN** 规则抽到 clock 但存在未消费日/段时间残留（半命中）
- **AND** 构建 classify 提示
- **THEN** 预解析块 SHALL 标明 partial/不完整
- **AND** MUST NOT 仅以残缺「今日 N 点」作为强制采用值

### Requirement: 分类时间提示瘦身与禁止逐步推算 Unix
意图分类 system 提示 MUST 避免冗长的「由口语逐步换算为 Unix」教学（如大段日段换算步骤、无钟点时长手算长文），改为引导：有非 partial 预解析时优先采用其 unix；内部思考（reasoning）MUST 使用中文，且 MUST NOT 逐步推算 Unix 时间戳。提示仍 MUST 保留 `start_time`/`end_time` 字段语义、计时开表与闭合补记的区分、`ignore_time_range`、以及多事件各自带时间等必要约束。

#### Scenario: 有预解析时提示要求优先采用而非手算
- **WHEN** 分类 system 提示已包含非 partial 预解析钟点
- **THEN** 提示条文 SHALL 要求优先采用预解析 unix（或语义等价）
- **AND** SHALL 约束 reasoning 不要逐步推算 Unix

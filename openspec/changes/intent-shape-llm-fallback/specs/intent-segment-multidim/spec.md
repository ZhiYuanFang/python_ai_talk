## MODIFIED Requirements

### Requirement: 段内多维顺序与事件向量门槛
段内解析顺序 SHALL 为类型 → 事件 →（事件已定后）明细备注 → 形态 → 量 → 时间。事件维 MUST 按阶梯尝试：正式名词典匹配 → `extra_names` 精确命中 → 短说法向量（相似度门槛 **0.72**）→ Go 备注模糊反查 → 事件小 LLM（若已实现）；任一步唯一命中即可定事件并进入后续维。形态维对计时叶 SHALL 按 `intent-shape-llm-fallback`：规则结束线索优先，暧昧时 SHAPE 小 LLM，不得仅由 `create`+`type=time` 无脑默认 start。类型维在存在句级类型上下文时 MUST 优先服从句级。

#### Scenario: 句级 history 压过段内口语
- **WHEN** 句级上下文为 history 且段文本为「今天换尿布了」类口语
- **THEN** 该段类型维 SHALL 保持查史（read），MUST NOT 仅因「了」记为 create

#### Scenario: 睡醒了不默认开表
- **WHEN** 段为「睡醒了」且事件维定为睡眠 time 叶
- **THEN** 形态维 SHALL 定为结束语义
- **AND** MUST NOT 因 create+time 默认推导而确认「现在开始睡眠」

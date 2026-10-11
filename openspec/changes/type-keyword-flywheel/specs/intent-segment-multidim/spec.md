## MODIFIED Requirements

### Requirement: 段内多维顺序与事件向量门槛
段内解析顺序 SHALL 为类型 → 事件 →（事件已定后）明细备注 → 量 → 时间。类型维 MUST：句级 `target_type`（若有）优先 → **类型关键字向量飞轮** → TYPE 小 LLM；MUST NOT 以「句内含睡/吃等弱喂养词」单独打成 create 并跳过飞轮与 TYPE LLM。开表/结束等形态 SHALL 由 TYPE 的 `op`（或等价）表达，MUST NOT 再插入独立必经的 SHAPE 小 LLM 维。事件维 MUST 按阶梯：正式名词典 → `extra_names` → 短说法向量（相似度门槛 **0.72**）→ Go 备注模糊反查 → 事件小 LLM；任一步唯一命中即可定事件。TIME / QTY SHALL 先规则，规则 miss（含时间半命中）后再小 LLM。

#### Scenario: 句级 history 压过段内口语
- **WHEN** 句级上下文为 history 且段文本为「今天换尿布了」类口语
- **THEN** 该段类型维 SHALL 保持查史（read），MUST NOT 仅因「了」记为 create

#### Scenario: 类型先飞轮再 LLM
- **WHEN** 无句级 type 且类型关键字库未命中「睡了多久了」
- **THEN** 系统 SHALL 调用 TYPE 小 LLM
- **AND** MUST NOT 因段含「睡」而直接 feeding+create

#### Scenario: EVENT 先别名再向量再反查再小 LLM
- **WHEN** 段文本为字典外实例词且某事件 `extra_names` 精确命中该词
- **THEN** 事件维 SHALL 在短说法向量、Go 反查与事件小 LLM 之前以该字典事件定稿

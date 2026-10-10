## MODIFIED Requirements

### Requirement: 单事件零 LLM 多维拼装
当系统判定用户输入为单事件时，MUST 跳过分句 LLM 与满血结构化分类 LLM，MUST 将整句作为唯一段执行类型/事件/形态/量/时间多维解析并拼装意图结果。事件已定后，系统 SHALL 按 `intent-segment-remark` 调用**明细备注**小 LLM（可返回空）；该调用 MUST NOT 视为满血多 events 分类，MUST NOT 恢复一次结构化主路径。

#### Scenario: 短句记奶
- **WHEN** 用户输入「吃了120奶」且判定为单事件
- **THEN** 系统 SHALL NOT 调用分句 LLM
- **AND** SHALL 经多维拼装得到带 quantity 的 create 类叶子事件（或等价 events[] 一项）

#### Scenario: 单事件可抽明细备注
- **WHEN** 用户输入「尿尿了，这次有点黄」且判定为单事件、事件维已定为尿尿
- **THEN** 系统 SHALL NOT 调用分句 LLM 或满血多 events 分类
- **AND** SHALL 允许调用明细备注小 LLM 并写出非空 `remark`

### Requirement: 段内多维顺序与事件向量门槛
段内解析顺序 SHALL 为类型 → 事件 →（事件已定后）明细备注 → 形态 → 量 → 时间。事件维 MUST 按阶梯尝试：正式名词典匹配 → `extra_names` 精确命中 → 短说法向量（相似度门槛 **0.72**）→ Go 备注模糊反查；任一步唯一命中即可定事件并进入后续维。类型维在存在句级类型上下文时 MUST 优先服从句级，不得被段内「…了」口语单独打成 create。

#### Scenario: 句级 history 压过段内口语
- **WHEN** 句级上下文为 history 且段文本为「今天换尿布了」类口语
- **THEN** 该段类型维 SHALL 保持查史（read），MUST NOT 仅因「了」记为 create

#### Scenario: EVENT 先别名再向量再反查
- **WHEN** 段文本为字典外实例词且某事件 `extra_names` 精确命中该词
- **THEN** 事件维 SHALL 在短说法向量与 Go 反查之前以该字典事件定稿
- **AND** `remark` SHALL 为该别名词

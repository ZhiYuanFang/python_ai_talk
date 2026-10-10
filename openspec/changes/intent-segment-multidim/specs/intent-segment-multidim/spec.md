## ADDED Requirements

### Requirement: 单事件零 LLM 多维拼装
当系统判定用户输入为单事件时，MUST 跳过分句 LLM 与满血结构化分类 LLM，MUST 将整句作为唯一段执行类型/事件/形态/量/时间多维解析并拼装意图结果。

#### Scenario: 短句记奶
- **WHEN** 用户输入「吃了120奶」且判定为单事件
- **THEN** 系统 SHALL NOT 调用分句 LLM
- **AND** SHALL 经多维拼装得到带 quantity 的 create 类叶子事件（或等价 events[] 一项）

### Requirement: 复合句仅 LLM 分句再段级多维
当判定为复合句（或单事件判定不确定）时，系统 SHALL 调用 LLM **仅分句**（MAY 附带句级 `target_type`），MUST NOT 要求该次 LLM 输出完整多 events 结构化落库 JSON。分句后 MUST 对每一段独立执行多维解析再拼装。

#### Scenario: 四事并列
- **WHEN** 用户输入「换尿布了，洗澡了，吃了120奶，睡觉了」
- **THEN** 系统 SHALL 得到不少于 2 段的分句结果并逐段多维
- **AND** SHALL NOT 因整句近邻某一历史「拉屎」说法而只落一条拉屎并丢弃其余段

### Requirement: 分句不得抹掉查史信号
分句输出 MUST 保留对各段成立的查史/次数/日词等类型信号（或通过句级 `target_type`/`history` 线索继承）。MUST NOT 将「今天 A 和 B 几次了」改写成不含「几次」的 create 口语而导致误记。

#### Scenario: 今天两件几次
- **WHEN** 用户输入「今天换尿布和喝奶几次了」
- **THEN** 各段多维结果的 `op` SHALL 为 `read`（或句级 history 下等价查史）
- **AND** SHALL NOT 将「换尿布」段解析为无次数信号的 create

### Requirement: 段内多维顺序与事件向量门槛
段内解析顺序 SHALL 为类型 → 事件 → 形态 → 量 → 时间。事件维向量相似度门槛 SHALL 为 **0.72**（与既有高置信阈值一致）。类型维在存在句级类型上下文时 MUST 优先服从句级，不得被段内「…了」口语单独打成 create。

#### Scenario: 句级 history 压过段内口语
- **WHEN** 句级上下文为 history 且段文本为「今天换尿布了」类口语
- **THEN** 该段类型维 SHALL 保持查史（read），MUST NOT 仅因「了」记为 create

### Requirement: 失败引导重说禁止回退一次结构化
当分句失败，或任一段在类型维与事件维均无法得到可用结果时，系统 MUST 向用户返回引导重新表述的说明，MUST NOT 回退到一次结构化多 events 的旧分类主路径。

#### Scenario: 分句失败
- **WHEN** 分句 LLM 未产出可用段列表
- **THEN** 响应 SHALL 引导用户重说
- **AND** SHALL NOT 调用已删除的满血多 events 分类主路径

### Requirement: 删除一次结构化主路径
系统 MUST NOT 再将「整表事件字典 + 一次输出完整 events[]（含 op/quantity/unix 等）」作为意图冷/热路径的默认分类契约。遗留提示词与节点若仍存在 MUST 不再被意图主图调用。

#### Scenario: 主图不进满血 classify
- **WHEN** 构建并执行改造后的意图主路径
- **THEN** 系统 SHALL NOT 以满血 `INTENT_CLASSIFICATION` 多 events JSON 作为默认产出步骤

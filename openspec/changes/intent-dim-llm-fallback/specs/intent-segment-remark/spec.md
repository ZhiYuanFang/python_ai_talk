## MODIFIED Requirements

### Requirement: EVENT miss 后段级 Go 备注反查
当段 EVENT 维经词典名、`extra_names`、短说法向量均未得到可用 `event_id` 时，系统 SHALL 以该段原文或剥离钟点/量词后的核心词作为 `remark` 关键字，调用与既有备注反查相同的 Go filter（本设备、近窗、小 limit、空 `eventIds`）做模糊反查。唯一叶命中时 MUST 写入该叶子 `event_id`/`event_name`，并将用于反查的关键字写入 `remark`。多叶命中 MUST 消歧。零命中时 MUST NOT 新建事件类型，MUST NOT 用常识升格为某字典类别而跳过反查；SHALL 进入 `intent-dim-llm-fallback` 的 EVENT 小 LLM，仅当小 LLM 仍空时才引导重说或无法识别。

#### Scenario: AD 反查营养品
- **WHEN** 段文本核心词为「AD」，词典名与 `extra_names` 与短说法向量均未定事件，近窗备注含 AD 的记录均落在营养品
- **THEN** 段级备注反查后该段 SHALL 使用字典「营养品」与对应 `event_id`，且 `remark` 为 AD（或所用关键字）
- **AND** SHALL NOT 在反查前把全量 history 注入分句或满血分类 prompt

#### Scenario: 反查零命中再走事件小 LLM
- **WHEN** 段 EVENT 阶梯走至 Go 反查且近窗无命中
- **THEN** 系统 SHALL 调用 EVENT 小 LLM 尝试表内对齐
- **AND** 仅当小 LLM 仍未给出 `event_id` 时 SHALL 反馈无法识别或引导重说
- **AND** MUST NOT 设置新建事件类型并落库该专名

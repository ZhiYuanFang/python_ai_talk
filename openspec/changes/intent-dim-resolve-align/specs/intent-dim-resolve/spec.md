## ADDED Requirements

### Requirement: 维判定统一方法
系统 SHALL 对每个意图飞轮维提供显式解析入口，并按固定顺序判定：可选强规则/词典 → 整段飞轮命中则采用并跳过本维 LLM → 否则维小 LLM → 成功则以段整句原文为 document 回写该维飞轮。缺槽或解析失败时 SHALL 进入澄清/追问，且 MUST NOT 写入该维飞轮。

#### Scenario: 飞轮命中跳过维 LLM
- **WHEN** 段原文命中某维整段飞轮且 payload 合法
- **THEN** 系统 SHALL 采用该 payload
- **AND** MUST NOT 为此维再调用对应小 LLM

#### Scenario: 冷路径成功整段回写
- **WHEN** 某维飞轮未命中且维小 LLM 产出合法结果并被采用
- **THEN** 系统 SHALL 以该段完整原文作为 document 写入该维飞轮

### Requirement: 时间维保持无飞轮特例
时间维 MUST NOT 使用向量飞轮。系统 SHALL 以本地规则优先；规则不足时 MAY 调用 TIME 小 LLM，并 MUST 写入 rule_gap。时间维 MUST NOT 因「其它维飞轮已命中」而跳过规则不足时的 TIME LLM。

#### Scenario: 仅时间 miss 仍可调 TIME LLM
- **WHEN** OP/数量等飞轮均已命中但时间规则未覆盖且存在时间线索
- **THEN** 系统 MAY 调用 TIME 小 LLM
- **AND** MUST 写入时间维 rule_gap
- **AND** MUST NOT 写入时间向量飞轮

### Requirement: 缺层须具备同构 resolve
系统 SHALL 为 R·predict（channel + time_answer）与 U/D 定位策略提供与其它飞轮维同构的 `resolve` 路径（整段飞轮 → LLM → 整段回写）。定位策略 payload MUST NOT 持久化设备相关 historyId。

#### Scenario: 预测两维飞轮热路径
- **WHEN** 段已判定为 read 且 read_source=predict，且预测飞轮命中合法 channel 与 time_answer
- **THEN** 系统 SHALL 采用该两维
- **AND** MUST NOT 仅为补齐该两维再调用预测维小 LLM

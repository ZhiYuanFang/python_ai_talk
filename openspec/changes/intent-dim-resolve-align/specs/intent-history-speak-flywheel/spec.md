## ADDED Requirements

### Requirement: 查史播报飞轮硬切整段 document
查史点查播报策略飞轮（history_speak / read_speak）的 document MUST 为用户段级完整原文。系统 MUST NOT 以短关键词（如单独「多久了」「上次」）作为主命中或主回写策略。匹配阈值 MUST 从严：宁可未命中走播报维 LLM，也 MUST NOT 接受高风险短词误命中。

#### Scenario: 整句命中播报策略
- **WHEN** 用户段原文为「睡了多久了」且飞轮中存在同文（或等价整段）document，payload 含合法 point_pick 与 open_speak
- **THEN** 系统 SHALL 采用该策略且 MUST NOT 为此再调用播报策略小 LLM

#### Scenario: 禁止短词回写
- **WHEN** 播报策略小 LLM 成功解析 point_pick 与 open_speak
- **THEN** 系统 SHALL 以当前段完整原文写入飞轮
- **AND** MUST NOT 仅将抽取出的短关键词列表作为主 document 写入

### Requirement: 旧短词种子失效
系统 SHALL 在硬切后使既有短关键词形态的播报飞轮条目不再作为热路径主命中来源（清空集合，或检索时拒绝过短/非整段 document）。发版 MUST 提供整句种子（至少覆盖「睡了多久了」类点查话术）。

#### Scenario: 短词条目不热命中
- **WHEN** 库中仅残留 document=「多久了」的旧条目且用户输入为更长复合句
- **THEN** 系统 MUST NOT 仅凭该短词高相似而采用播报策略（应未命中或落入冷路径 LLM）

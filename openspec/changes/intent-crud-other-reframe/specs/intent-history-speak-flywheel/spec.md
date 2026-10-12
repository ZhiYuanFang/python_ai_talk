## MODIFIED Requirements

### Requirement: 缺维须调用查史播报小 LLM
当 read·record 点查路径上播报飞轮未命中，或命中但策略维缺省/非法时，系统 SHALL 调用查史播报小 LLM（提示词在 `prompts/system.py`），经 SSE 真流式并透出中文 reasoning。飞轮 document MUST 为段整句。系统 MUST NOT 在缺维时静默默认 prefer_completed。调用 MUST NOT 写入 rule_gap。

#### Scenario: 未命中整段飞轮走 LLM
- **WHEN** 点查段未命中查史播报整段飞轮
- **THEN** 系统 SHALL 调用查史播报小 LLM 解析播报/选行策略
- **AND** 成功采用后 MAY 以该段整句写入飞轮

## ADDED Requirements

### Requirement: 查史播报飞轮禁止短关键词主策略
查史播报飞轮 MUST NOT 以短关键词作为主 document 策略；存量短词种子 SHOULD 迁移为整句或清除，以免与「宁可不中不可错中」冲突。

#### Scenario: 拒绝以单独多久了为权威种子策略
- **WHEN** 管理端或运行时写入查史播报飞轮
- **THEN** 权威加速路径 SHALL 以完整段原文为准，而非单独「多久了」短词作为推荐主策略

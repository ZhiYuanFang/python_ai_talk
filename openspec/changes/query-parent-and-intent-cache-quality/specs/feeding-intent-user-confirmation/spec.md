## MODIFIED Requirements

### Requirement: 系统生成清晰的确认话术
系统 SHALL 根据意图结果生成清晰的确认话术，包含事件名称和动作描述。查记录确认 MUST 点出字典事件名（叶子或父），MUST NOT 使用「该事件」等不含名称的句子。

#### Scenario: 生成确认话术
- **WHEN** 系统识别到意图为"开始记录母乳"
- **THEN** 生成确认话术"您是要开始记录「母乳」吗？请回复「确认」或「取消」。"

#### Scenario: 生成查记录确认话术
- **WHEN** 系统识别到意图为查询「尿尿」历史且需要确认
- **THEN** `confirm_message` SHALL 包含「尿尿」
- **AND** SHALL NOT 使用「该事件」代替名称

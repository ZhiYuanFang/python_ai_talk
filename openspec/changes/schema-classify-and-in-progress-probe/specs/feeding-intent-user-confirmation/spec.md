## MODIFIED Requirements

### Requirement: 系统生成清晰的确认话术
系统 SHALL 根据意图结果生成清晰的确认话术，包含事件名称和动作描述。查记录确认 MUST 点出字典事件名（叶子或父），MUST NOT 使用「该事件」等不含名称的句子。查记录确认话术 MUST 仅在 `op=read` 时使用；MUST NOT 仅因 `action=search` 就把删除、修改或记录说成查询历史。当 `events[]` 含多项或同时含结束与开始/记录时，确认话术 MUST 逐项点出字典事件名与对应动作（结束 / 开始 / 记录），MUST NOT 仅列举名称并写成「记录以下事件」。删除确认 MUST 点出事件名与删除含义。

#### Scenario: 生成确认话术
- **WHEN** 系统识别到意图为"开始记录母乳"
- **THEN** 生成确认话术"您是要开始记录「母乳」吗？请回复「确认」或「取消」。"

#### Scenario: 生成查记录确认话术
- **WHEN** 系统识别到意图为查询「尿尿」历史且需要确认（`op=read`）
- **THEN** `confirm_message` SHALL 包含「尿尿」
- **AND** SHALL NOT 使用「该事件」代替名称

#### Scenario: 复合切换确认点出结束与开始
- **WHEN** 分类结果为结束「爬练习」并开始「坐练习」且需要确认
- **THEN** `confirm_message` SHALL 包含结束与爬练习
- **AND** SHALL 包含开始（或记录）与坐练习
- **AND** SHALL NOT 仅使用「记录以下事件：爬练习、坐练习」这类不区分动作的句子

#### Scenario: 删除不得说成查询
- **WHEN** 分类结果 `op=delete` 且事件为坐练习，即使 `action` 为 `search`
- **THEN** `confirm_message` SHALL 表达删除坐练习
- **AND** SHALL NOT 使用「是否查询「坐练习」的历史」

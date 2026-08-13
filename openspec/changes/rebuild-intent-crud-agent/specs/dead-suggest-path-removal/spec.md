## MODIFIED Requirements

### Requirement: Suggest generation does not use suggest_answer module
系统 SHALL NOT 再通过 `suggest_answer` 提示词模块生成 intent suggest 回答。意图图 SHALL NOT 再路由 `target_type=suggest` 到 clinic agent。成长建议与陪伴长文 SHALL 由 clinic HTTP（`/v1/clinic` 或 `/v1/clinic/stream`）承担。

#### Scenario: suggest_answer module removed
- **WHEN** 代码库完成本变更
- **THEN** 仓库中 SHALL NOT 存在被运行时引用的 `suggest_answer` 提示词模块（文件删除或无任何 import）

#### Scenario: intent 无 suggest 进 clinic
- **WHEN** 用户在 `/v1/analyze/intent` 输入成长建议类问题
- **THEN** 意图图 SHALL NOT 调用 `call_clinic_agent`
- **AND** MAY 将其作为 conversation 短回复；完整建议走 clinic 入口

### Requirement: generate_response serves history only
意图图查记录 SHALL 使用模板填写 `content`，MUST NOT 再按 `target_type == "suggest"` 选择建议提示词，MUST NOT 再调用历史答题 LLM。若仍保留同步生成节点，该节点 MUST NOT 被意图查记录主路径调用。

#### Scenario: History short chain still works
- **WHEN** intent 路由到查记录
- **THEN** 系统 SHALL 使用模板填写 `content`
- **AND** SHALL NOT 调用历史答题 LLM

#### Scenario: No suggest branch in generate_response
- **WHEN** 检查查记录生成实现
- **THEN** 代码中 SHALL NOT 存在选择 `suggest_answer` 或等价 suggest 专用提示词的分支

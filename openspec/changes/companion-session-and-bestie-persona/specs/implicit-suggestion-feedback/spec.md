## ADDED Requirements

### Requirement: Judge previous suggestion before clinic reply
在 clinic 流式请求生成新回答之前，若该 `device_no` 会话存在尚未完成飞轮处理的上一条建议（`feedback_applied` 为 false），系统 SHALL 根据用户本轮 `question` 与上一条建议内容，判定为 `accepted`、`rejected` 或 `unclear` 三态之一。

#### Scenario: Acceptance on follow-up
- **WHEN** 上一条建议待判定，且用户本轮表述明确表示会按建议做或采纳
- **THEN** 判定结果为 `accepted`

#### Scenario: Rejection on follow-up
- **WHEN** 上一条建议待判定，且用户本轮表述明确拒绝或不认同该建议
- **THEN** 判定结果为 `rejected`

#### Scenario: Unclear on follow-up
- **WHEN** 上一条建议待判定，且用户本轮与采纳态度无关或态度不明
- **THEN** 判定结果为 `unclear`

### Requirement: Tip opening counts as pending suggestion
tip 开场成功写入会话后，系统 SHALL 将其标记为待判定建议，使得随后同一 `device_no` 的首次 clinic 续聊可以触发三态判定。

#### Scenario: First clinic message judges tip
- **WHEN** tip 开场已写入且 `feedback_applied` 为 false，用户首次调用 clinic 续聊
- **THEN** 系统在生成 clinic 回答前对 tip 开场建议执行三态判定

### Requirement: Flywheel updates only on accept or reject
系统 SHALL 仅在判定为 `accepted` 或 `rejected` 时，对上一条建议关联的知识文档 `knowledge_ids` 调用质量分更新（接受上调、拒绝下调）；`unclear` SHALL NOT 修改质量分。

#### Scenario: Accepted updates quality scores
- **WHEN** 判定为 `accepted` 且 `knowledge_ids` 非空
- **THEN** 系统对这些文档执行与正面反馈等价的质量分更新

#### Scenario: Unclear does not change scores
- **WHEN** 判定为 `unclear`
- **THEN** 系统不修改任何知识文档质量分

#### Scenario: No knowledge ids skips score update
- **WHEN** 判定为 `accepted` 或 `rejected` 但 `knowledge_ids` 为空
- **THEN** 系统不调用质量分更新，且不报错中断主流程

### Requirement: Each suggestion judged at most once after successful classification
当三态判定成功完成（得出 `accepted`、`rejected` 或 `unclear`）后，系统 SHALL 将该条建议标记为 `feedback_applied=true`，后续请求 SHALL NOT 再次对其飞轮加减分。

#### Scenario: Second clinic turn does not re-judge same suggestion
- **WHEN** 上一条建议已 `feedback_applied=true`
- **THEN** 下一次 clinic 请求跳过对该条建议的飞轮更新

#### Scenario: Judge failure allows retry
- **WHEN** 判定过程因异常失败且未得到三态结果
- **THEN** 系统不将 `feedback_applied` 置为 true，且不中断后续回答生成

### Requirement: Explicit feedback endpoints remain available
系统 SHALL 继续提供现有的 clinic/tip 显式 feedback HTTP 接口；隐式判定 SHALL NOT 删除这些接口。

#### Scenario: Explicit feedback still accepted
- **WHEN** 客户端调用现有 feedback 接口并提交合法 feedback 值
- **THEN** 系统按既有契约接受请求（与隐式飞轮可并存）

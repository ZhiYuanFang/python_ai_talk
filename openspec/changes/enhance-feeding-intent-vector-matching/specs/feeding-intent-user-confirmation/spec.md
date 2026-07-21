## ADDED Requirements

### Requirement: 系统在喂养意图落库前询问用户确认
系统 SHALL 在识别到喂养意图后，根据置信度决定是否需要用户确认，使用LangGraph interrupt机制暂停图执行。

#### Scenario: 中等置信度需要确认
- **WHEN** 向量匹配置信度为92%
- **THEN** 系统生成确认话术
- **AND** 暂停图执行，等待用户反馈
- **AND** 返回确认请求给调用方

#### Scenario: 用户确认执行
- **WHEN** 用户回复"确认"
- **THEN** 系统继续图执行
- **AND** 返回喂养意图结果给调用方

#### Scenario: 用户否定
- **WHEN** 用户回复"取消"
- **THEN** 系统根据置信度处理（≥90%删除向量数据）
- **AND** 返回对话意图，让用户重新描述

### Requirement: 系统生成清晰的确认话术
系统 SHALL 根据意图结果生成清晰的确认话术，包含事件名称和动作描述。

#### Scenario: 生成确认话术
- **WHEN** 系统识别到意图为"开始记录母乳"
- **THEN** 生成确认话术"您是要开始记录「母乳」吗？请回复「确认」或「取消」。"

### Requirement: 系统支持用户反馈的两种状态
系统 SHALL 支持用户反馈的两种状态：确认（confirm）和否定（reject）。

#### Scenario: 处理确认反馈
- **WHEN** 用户反馈为"confirm"
- **THEN** 系统继续执行落库流程

#### Scenario: 处理否定反馈
- **WHEN** 用户反馈为"reject"
- **THEN** 系统取消落库流程
- **AND** 返回对话意图

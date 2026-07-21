## MODIFIED Requirements

### Requirement: 确认接口适配兄弟仓
系统 SHALL 调研 go_ai_talk 和 flutter_ai_talk 是否需要修改以适配 `/v1/analyze/intent/confirm` 接口。

#### Scenario: go_ai_talk 适配调研
- **WHEN** 调研 go_ai_talk 的意图分析调用逻辑
- **THEN** 检查是否需要处理 need_confirm 响应
- **AND** 检查是否需要调用 confirm 接口
- **AND** 输出适配需求文档

#### Scenario: flutter_ai_talk 适配调研
- **WHEN** 调研 flutter_ai_talk 的 UI 交互流程
- **THEN** 检查是否需要新增确认弹窗组件
- **AND** 检查是否需要处理确认/取消用户交互
- **AND** 输出适配需求文档

#### Scenario: 无需适配
- **WHEN** 调研结果显示兄弟仓无需修改
- **THEN** 记录调研结论
- **AND** 标记适配任务为完成

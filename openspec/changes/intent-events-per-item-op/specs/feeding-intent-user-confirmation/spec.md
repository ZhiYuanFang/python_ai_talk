## ADDED Requirements

### Requirement: 确认话术按子项 op 与事件名生成
当 `events` 含多项或同时含结束与开始/记录时，确认话术 MUST 逐项点出字典事件名与对应操作含义（结束 / 开始或记录 / 修改 / 删除），MUST NOT 依赖顶层 `action=multi`，MUST NOT 仅列举名称并写成「记录以下事件」。

#### Scenario: 结束睡眠并开始爬练习的确认
- **WHEN** `events` 为睡眠 `op=end` 与爬练习 `op=create`
- **THEN** `confirm_message` SHALL 表达结束睡眠并开始（或记录）爬练习

### Requirement: 确认后续聊保留完整 events
用户确认后，系统 SHALL 保留 pending 中的完整 `events`（含各子项 `op`）进入执行，MUST NOT 只保留第一项，MUST NOT 用顶层 `op`/`action` 重建子项语义。

#### Scenario: 确认后执行复合项
- **WHEN** 用户对复合确认回复肯定且 conversation 有效
- **THEN** 执行路径 SHALL 看到与确认前一致的多子项 `events`
- **AND** 各子项 `op` SHALL 仍可用于 batch 组装

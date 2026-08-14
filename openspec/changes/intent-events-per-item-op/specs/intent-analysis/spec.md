## ADDED Requirements

### Requirement: 分类产出以 events 子项表达涉事件意图
`classify_intent`（及等价分类）在识别喂养增删改结束或查记录时，SHALL 产出非空 `events[]`，每项含字典叶子（或可解析的名称槽）与子项 `op`。分类结果 MUST NOT 依赖顶层 `op` 或顶层 `action` 表达 CRUD、读或多事件。闲聊与退出 SHALL 以 `target_type`（及 `content`）表达，不必填充 `events`。

#### Scenario: 复合切换分类
- **WHEN** 用户说结束一件计时并开始另一件计时
- **THEN** 分类结果 `events` SHALL 含 `op=end` 与 `op=create` 两项
- **AND** 响应 MUST NOT 要求顶层 `action=multi` 才成立

#### Scenario: 查记录分类
- **WHEN** 用户查询某叶子历史
- **THEN** `target_type` SHALL 为 `history`（或等价）
- **AND** `events` SHALL 含至少一项 `op=read` 且带事件标识与时间窗字段（可估算）

#### Scenario: 结束不是 update
- **WHEN** 用户仅结束进行中计时
- **THEN** 对应子项 `op` SHALL 为 `end`
- **AND** MUST NOT 将结束语义标为 `update`

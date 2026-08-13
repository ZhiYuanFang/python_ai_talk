## ADDED Requirements

### Requirement: 复合切换句须拆成多子项且各带动作
当用户一句话同时表达停止一件已有事件并开始或记录另一件已有事件时，意图分析结果 SHALL 在 `events` 中给出至少两个子项，停止项 `action` MUST 为 `end`，另一项 `action` MUST 为 `start` 或 `one`，且 MUST 使用事件字典中的叶子 id。系统 MUST NOT 将此类句子分类为单事件 create。

#### Scenario: 现在不爬了改坐了
- **WHEN** 客户端发送意图请求，`text` 为「现在不爬了，改坐了」，且字典含爬练习与坐练习
- **THEN** 响应（或待确认的意图）SHALL 含 `events` 两项以上
- **AND** 其中一项 SHALL 为爬练习且 `action=end`
- **AND** 另一项 SHALL 为坐练习且 `action` 为 `start` 或 `one`

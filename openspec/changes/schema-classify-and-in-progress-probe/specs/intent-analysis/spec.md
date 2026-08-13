## ADDED Requirements

### Requirement: 删除最近一次记录不得分类为查记录
当用户要去掉某件已有事件最近一次记录时，意图分析结果 `op` SHALL 为 `delete`，MUST NOT 为 `read`。系统 MUST NOT 用匹配「上一次」的本地规则把该句定为查询。

#### Scenario: 删除上一次坐练习
- **WHEN** 客户端发送意图请求，`text` 为「删除上一次坐练习的记录」，且字典含坐练习
- **THEN** 响应或待确认意图的 `op` SHALL 为 `delete`
- **AND** SHALL NOT 为 `read`
- **AND** 确认话术若需要确认 SHALL 表达删除而非查询历史

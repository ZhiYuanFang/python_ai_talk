## ADDED Requirements

### Requirement: 次数问语境下 number 聚合须暴露次数
当调用方以次数问语境使用共享喂养史紧凑聚合（或 speak 层基于该聚合拼句）时，对 `number` 类型事件组，系统 SHALL 能提供或拼出发生次数（组内记录条数），MUST NOT 仅有毫升总量段作为次数问的唯一答案来源。非次数问语境 MAY 继续以总量段为主。

#### Scenario: number 组可得到条数
- **WHEN** 某日历日×事件名下有 2 条 number 类型喝水记录
- **AND** 上层以次数问语义消费聚合结果
- **THEN** 次数信息 SHALL 为 2（或文案含「2次」）
- **AND** 毫升总量 MAY 同时存在但不替代次数

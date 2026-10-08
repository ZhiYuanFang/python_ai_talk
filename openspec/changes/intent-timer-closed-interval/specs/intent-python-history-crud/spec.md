## ADDED Requirements

### Requirement: 计时 create 尊重显式结束时间
将意图转为 Go batch 子项时，对字典 `event_type=time` 的 create：若子项 `end_time`（或等价字段）大于 0，系统 SHALL 将该值作为 `endTime` 提交，MUST NOT 强制改为 0。仅当未提供有效结束时间时，计时 create 的 endTime SHALL 为 0（开表）。瞬时非计时 create 的 endTime 仍与 startTime 对齐的既有行为 MUST NOT 因本条破坏。

#### Scenario: 显式 end 不被抹掉
- **WHEN** 意图 events 含计时 create 且 end_time 为某正 Unix 秒、start_time 更早
- **THEN** batch item 的 endTime SHALL 等于该 end_time
- **AND** MUST NOT 为 0

#### Scenario: 无 end 仍开表
- **WHEN** 计时 create 无有效 end_time
- **THEN** batch item 的 endTime SHALL 为 0

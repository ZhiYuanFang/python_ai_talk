## MODIFIED Requirements

### Requirement: 多段确认策略 C
多段拼装完成后，系统 SHALL 先处理阻塞澄清（父消歧、缺量追问、多叶消歧）。若无阻塞且各段均为可执行叶子，系统 SHALL 直接执行（短同质可一次 batch；混 op 按执行路径拆分），MUST NOT 再用「您是要 A 并 B 吗？」类拼问等待用户肯定。仅当仍存在必须由用户选择的选项时，才保留澄清问句。

#### Scenario: 短同质直执行
- **WHEN** 两段均为 create 叶子且槽位齐全、无阻塞
- **THEN** 系统 SHALL 直接执行两段落库（或一次 batch）
- **AND** MUST NOT 先发送拼接确认问句等待「是的」

#### Scenario: 混装不拼 yes/no
- **WHEN** 拼装结果同时含 create 与 read 且均无阻塞
- **THEN** 系统 SHALL 按路径执行写库与查史（可分步执行）
- **AND** MUST NOT 用单条 yes/no 同时确认写库与查史

## ADDED Requirements

### Requirement: 完整叶子不再默认 leaf_confirm
当单段或多段结果在阻塞澄清之后仅剩已定叶子 CRUD/查史时，系统 MUST NOT 再进入默认的 `leaf_confirm` 自由文本确认。

#### Scenario: 单段结束睡眠
- **WHEN** 单段为已定叶子结束睡眠且无阻塞
- **THEN** 响应 SHALL 为执行回执（成功或业务失败如无可结束项）
- **AND** SHALL NOT 为 `leaf_confirm` pending

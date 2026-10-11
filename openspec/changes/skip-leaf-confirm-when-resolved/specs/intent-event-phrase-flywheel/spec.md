## MODIFIED Requirements

### Requirement: 确认后只写短说法
用户确认（或等价成功落库/成功查史执行）后，系统 MAY 将 **段级** 原文或规范化短句写入事件说法库并关联所确认叶子/父事件。在「拼装完整直执行」路径下，短说法写入 MUST 以**执行成功**为触发，MUST NOT 依赖 `leaf_confirm` 用户点头。MUST NOT 写入未拆分的复合整句作为 document。

#### Scenario: 复合句确认后分条写入
- **WHEN** 用户确认包含多段 create 的拼装结果且落库成功
- **THEN** 系统 MAY 为各段分别写入短说法
- **AND** MUST NOT 将整句复合原文作为单条 document 绑定单一叶子

#### Scenario: 直执行成功后写短说法
- **WHEN** 「睡醒了」无 leaf_confirm 直接结束睡眠落库成功
- **THEN** 系统 MAY 将段说法「睡醒了」写入短说法库关联睡眠
- **AND** MUST NOT 因未走 leaf_confirm 而拒绝写入

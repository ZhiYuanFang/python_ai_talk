## ADDED Requirements

### Requirement: 顶层意图轨须为 CRUD 与 exit/other
系统 SHALL 以段级意图轨区分 `create`、`read`、`update`、`delete`、`exit`、`other`（对应 C/R/U/D/exit/other）。系统 MUST NOT 再以 `feeding`/`history`/`predict`/`conversation`/`suggest` 作为主路由枚举。非喂养 CRUD 且非 exit 的段 SHALL 归为 `other`。

#### Scenario: 记录类进 create
- **WHEN** 用户段意为新记一条喂养事件（如「睡着了」「吃了 120 奶」）
- **THEN** 该段意图轨 SHALL 为 `create`

#### Scenario: 查问类进 read
- **WHEN** 用户段意为查询已发生或预测类问答（如「睡了多久了」「还有多久醒来」）
- **THEN** 该段意图轨 SHALL 为 `read`

#### Scenario: 非喂养进 other
- **WHEN** 用户段既非喂养 C/R/U/D 也非退出
- **THEN** 意图轨 SHALL 为 `other`
- **AND** 回复 SHALL 表明暂不支持
- **AND** MUST NOT 因此结束会话（不同于 exit）

### Requirement: 复合句段循环与统一汇总
系统 SHALL 将复合句拆为段后逐段执行对应 CRUD 轨。任一段的失败或需追问 MUST NOT 阻断后续段的处理。全部段处理完成后，系统 SHALL 在一次回复中汇总各段结果与待补充信息。

#### Scenario: 一段需追问另一段成功
- **WHEN** 复合句含两段，一段 create 成功，一段缺量需追问
- **THEN** 最终回复 SHALL 同时包含成功结果说明与缺量追问
- **AND** MUST NOT 因追问而跳过已成功段的执行

### Requirement: end 语义归 update 轨
计时结束类说法（如「睡醒了」）SHALL 归入 `update` 轨：系统 SHALL 在时间窗内查找对应事件「仅有 start、无有效 end」的进行中记录；若存在则更新该记录（补 end）；若不存在，系统 SHALL 将该段转入 `create` 轨逻辑。

#### Scenario: 有进行中则更新
- **WHEN** 用户说睡醒了且存在未结束的睡眠进行中记录
- **THEN** 系统 SHALL 对该记录执行更新补 end

#### Scenario: 无进行中则转 create
- **WHEN** 用户说睡醒了但不存在未结束的对应进行中记录
- **THEN** 系统 SHALL 转入 create 逻辑并按事件叶子类型决定落库形态

### Requirement: 转 create 后按叶子类型落库或追问
当段从 update·end 转入 create，或本即为 create 时，系统 SHALL 按事件叶子 `one|number|time` 选择形态：`one`→create+one；`number`→create+number（无量线索则追问）；`time`→须具备可闭合的 start 与 end，否则 SHALL 向用户追问起止，MUST NOT 臆造闭合区间。

#### Scenario: time 无闭合则追问
- **WHEN** create 轨事件为 time 叶且无法得到闭合 start/end
- **THEN** 该段结果 SHALL 为需补充时间信息
- **AND** MUST NOT 写入无闭合的虚假 time 区间

### Requirement: 一期写库仍可走 batch
一期实现中，create/update/delete 分轨编排完成后，系统 MAY 继续通过 Go `event/batch`（或等价打包接口）提交。系统 MUST 在分轨语义上区分 C/U/D，不得因 batch 外形而恢复顶层 feeding/history/predict 混淆。

#### Scenario: update 经 batch 提交
- **WHEN** update 轨已定位 historyId 并完成字段组装
- **THEN** 一期 MAY 经 batch 提交该更新
- **AND** 业务语义 SHALL 仍为更新指定记录

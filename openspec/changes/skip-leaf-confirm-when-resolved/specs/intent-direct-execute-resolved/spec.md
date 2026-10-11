## ADDED Requirements

### Requirement: 拼装完整且无阻塞时直接执行
当段多维（或等价拼装）产出 feeding/history 意图，且全部相关事件已定 `event_id`、无 number 缺量、无父消歧/多叶消歧等待用户选择时，系统 SHALL 直接进入批量落库或模板查史执行路径，MUST NOT 再创建 `leaf_confirm` 或向用户发出「您是要…吗？」类二次确认问句。

#### Scenario: 睡醒了直结束
- **WHEN** 用户输入「睡醒了」且拼装为睡眠 `op=end`（或等价结束计时）且无阻塞澄清
- **THEN** 系统 SHALL 直接调用结束计时落库（或等价 batch）
- **AND** MUST NOT 先返回「您是要现在结束「睡眠」吗？」并等待肯定答复

#### Scenario: 记奶有量直落库
- **WHEN** 用户输入「吃了120奶」且拼装为 number 叶 create 且 quantity=120
- **THEN** 系统 SHALL 直接落库
- **AND** MUST NOT 要求用户再确认一次

### Requirement: 阻塞澄清仍须用户交互
当存在父事件消歧、number 叶缺量追问、或备注/别名多叶消歧时，系统 MUST 先完成该澄清，MUST NOT 在澄清完成前直接落库或正式拉史。

#### Scenario: 缺量仍追问
- **WHEN** number 叶 create 且 quantity 为空
- **THEN** 系统 SHALL 追问数量
- **AND** SHALL NOT 直接落库

#### Scenario: 父消歧仍问
- **WHEN** create 命中父事件
- **THEN** 系统 SHALL 发起子选项消歧
- **AND** SHALL NOT 跳过消歧直接落库

### Requirement: 维级 LLM 命中不单独强制确认
系统 MUST NOT 仅因 `match_source` 为 llm（或事件/形态小 LLM 参与拼装）而强制进入 `leaf_confirm`。是否确认仅取决于是否存在阻塞澄清或显式未决槽位。

#### Scenario: EVENT LLM 命中可直执行
- **WHEN** 事件由 EVENT 小 LLM 定为表内叶子且无其它阻塞
- **THEN** 系统 SHALL 允许直接执行
- **AND** MUST NOT 仅因 match_source=llm 而二次确认

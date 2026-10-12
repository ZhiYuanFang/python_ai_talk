## ADDED Requirements

### Requirement: 飞轮 document 须为整段原文
各意图飞轮集合的 `document` MUST 为段级完整原文（或等价完整单句口语）。系统 MUST NOT 以短关键词（如单独「多久了」）作为主命中 document 策略。匹配阈值 MUST 从严：宁可未命中进入冷路径，也 MUST NOT 接受高风险短词误命中。

#### Scenario: 整段写入数量飞轮
- **WHEN** QTY 小 LLM 从「喂了差不多一百二」解析出 quantity 并采用
- **THEN** 系统 SHALL 可用该整段原文作为 document 写入数量飞轮

### Requirement: 分层飞轮清单
系统 SHALL 支持（可分阶段落地）以下整段飞轮层，且各层独立集合或等价隔离空间：OP 轨、事件、数量、R·数据源（record|predict）、R·record 播报、R·predict 播报、U/D 定位策略。定位策略 payload MUST NOT 直接持久化设备相关 `historyId`。

#### Scenario: OP 命中跳过 OP LLM
- **WHEN** 段原文命中 OP 飞轮且 payload 为合法 create|read|update|delete|exit|other
- **THEN** 系统 SHALL 采用该轨且 MUST NOT 为此再调用 OP 分类小 LLM

### Requirement: 时间维禁止向量飞轮
时间解析 MUST NOT 依赖时间向量飞轮。系统 SHALL 以本地规则优先；规则未覆盖时 MAY 调用 TIME 小 LLM，并 MUST 写入规则缺口收件箱供人工扩规则。时间缺槽或 time 叶无闭合时 SHALL 追问用户。

#### Scenario: 时间 miss 写缺口不写时间飞轮
- **WHEN** 时间规则未能产出可用结果并调用 TIME LLM
- **THEN** 系统 SHALL 写入 rule_gap（时间维）
- **AND** MUST NOT 将时间解析结果作为时间向量飞轮的主加速手段

### Requirement: 数量维须支持飞轮
当存在数量线索且规则未能抽出 quantity 时，系统 SHALL 可调用 QTY 小 LLM，并 SHALL 将整段原文与 quantity 写入数量飞轮供热路径复用。完全无数量线索时，number 叶缺量追问 MUST NOT 写入数量飞轮。

#### Scenario: 口语量冷路径回写
- **WHEN** 「吃了差不多一瓶」经 QTY LLM 得到 quantity 并采用
- **THEN** 系统 SHALL 将该段写入数量飞轮
- **AND** 再次相同段原文时热路径 MAY 跳过 QTY LLM

### Requirement: 热路径少 LLM 目标
当某段所需飞轮层（OP、事件、数量、R 子维、定位策略等）均合法命中，且时间由规则满足时，系统 SHOULD 不调用对应维小 LLM 即可完成该段主路径。时间规则未满足时仍 MAY 调用 TIME LLM（不受「数量飞轮已命中」影响）。

#### Scenario: R 问答飞轮齐备
- **WHEN** 「睡了多久了」命中 OP=read、source=record 与 record 播报飞轮，且查史窗由规则可得
- **THEN** 系统 MAY 不调用 OP/R 播报小 LLM 完成播报主路径

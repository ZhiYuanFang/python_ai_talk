## ADDED Requirements

### Requirement: R·predict 整段飞轮层
系统 SHALL 维护独立（或等价隔离）的预测两维整段飞轮集合，document 为段完整原文，payload 含合法 predict_channel（active|next）与 time_answer（clock|remain）。该层与 OP 轨飞轮、R·source 飞轮 MUST 分离。

#### Scenario: 还有多久醒来可飞轮跳过预测 LLM
- **WHEN** 「还有多久醒来」已判定 read+predict，且预测飞轮命中合法两维
- **THEN** 系统 SHALL 采用该两维进入预测播报主路径
- **AND** MUST NOT 仅为该两维再调用预测维小 LLM

### Requirement: U/D 定位整段飞轮层
系统 SHALL 维护 U/D 定位策略整段飞轮，document 为段完整原文，payload 为策略码（不含设备相关 historyId）。命中后 SHALL 按策略查史选行；无法唯一定位时 SHALL 段级澄清。

#### Scenario: 定位飞轮不写 historyId
- **WHEN** 定位维 LLM 或规则确定选行策略并回写飞轮
- **THEN** 写入 payload MUST NOT 包含具体 historyId
- **AND** 执行时 SHALL 按策略码现查历史行

### Requirement: R·record 播报层须整段
R·record 播报飞轮（含演进自 history_speak 的集合）MUST 遵守整段 document 策略，与 OP/数量等层一致，MUST NOT 以短关键词为主策略。

#### Scenario: 与 OP 同严的整段策略
- **WHEN** 向 R·record 播报飞轮写入或检索
- **THEN** document MUST 为段整句原文且命中阈值从严

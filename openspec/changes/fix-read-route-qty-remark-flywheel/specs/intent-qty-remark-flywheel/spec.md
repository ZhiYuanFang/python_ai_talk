## ADDED Requirements

### Requirement: 数量维规则优先再飞轮
数量解析 MUST 按顺序：本地规则抽出 quantity；规则未得则检索数量整段飞轮；仍未得且存在真数量线索时 MAY 调用 QTY 小 LLM，成功采用后 SHALL 以段整句原文写入数量飞轮。完全无数量线索时，number 叶缺量追问 MUST NOT 写入数量飞轮。

#### Scenario: 口语量二次跳过 QTY LLM
- **WHEN** 「吃了差不多一百二」首次经 QTY LLM 得到 quantity 并回写飞轮
- **AND** 再次相同段原文且规则仍抽不出
- **THEN** 系统 SHALL 可从数量飞轮命中 quantity
- **AND** MUST NOT 为此再调用 QTY 小 LLM

### Requirement: 数量线索禁止裸中文数词
数量线索检测 MUST NOT 将孤立的「一」「二」等中文数词（未贴毫升/ml，且不在吃了/喝了/喂了后）视为真数量线索。

#### Scenario: 下一次不触发 QTY LLM
- **WHEN** 段原文为「下一次喂养是什么时候」且规则未抽出 quantity
- **THEN** 系统 MUST NOT 仅因含「一」而调用 QTY 小 LLM

### Requirement: 备注整段飞轮
系统 SHALL 支持备注整段飞轮：document 为段完整原文，payload 含 remark（允许空字符串表示已确认无明细）。事件已定且非 read 轨时：已有别名/反查备注可跳过 LLM；否则飞轮优先，未命中再明细备注 LLM，成功后整段回写。

#### Scenario: 空备注二次跳过备注 LLM
- **WHEN** 某 create 段经备注 LLM 得到空 remark 并写入飞轮
- **AND** 再次相同段原文且无更高优先级已有备注
- **THEN** 系统 SHALL 可采用飞轮空备注
- **AND** MUST NOT 为此再调用明细备注小 LLM

### Requirement: 读路径跳过备注与数量维
当段顶层轨为 read（含 read_source 为 record 或 predict）时，系统 MUST NOT 调用明细备注小 LLM，MUST NOT 调用 QTY 小 LLM，MUST NOT 为该段写入数量/备注飞轮。

#### Scenario: 预测问句不跑备注数量
- **WHEN** 段判定为 read 且 read_source=predict
- **THEN** 解析路径 MUST NOT 发起备注或数量维 LLM

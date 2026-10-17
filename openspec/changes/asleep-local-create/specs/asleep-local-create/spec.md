## ADDED Requirements

### Requirement: Asleep utterance is a local create

没有疑问词时，「睡着了」MUST 由记一笔本地规则判为 create。系统 MUST NOT 为此查询操作飞轮，也 MUST NOT 调用顶层轨模型。「睡醒了」MUST 仍为结束计时。「睡了多久」MUST 仍为查记录。

#### Scenario: Falling asleep skips the operation model

- **WHEN** 用户说「睡着了」
- **THEN** 操作轨 MUST 为记一笔
- **AND** MUST NOT 调用顶层轨模型

#### Scenario: Waking up stays an end

- **WHEN** 用户说「睡醒了」
- **THEN** 操作轨 MUST 仍为结束计时
- **AND** MUST NOT 判成记一笔

### Requirement: Asleep utterance is not a remark detail

判断是否还有备注明细时，系统 MUST 把「睡着了」与「睡了」一样剥掉。剥完没有剩余描述时，备注 MUST 为空，且 MUST NOT 查询备注飞轮，MUST NOT 调用备注模型。

#### Scenario: Asleep alone has an empty remark

- **WHEN** 用户说「睡着了」且事件已定
- **THEN** 备注 MUST 为空
- **AND** MUST NOT 调用备注抽取模型

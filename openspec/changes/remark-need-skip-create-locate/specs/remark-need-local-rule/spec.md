## ADDED Requirements

### Requirement: Empty detail skips remark flywheel and model

事件已定且别名没有备注时，系统 MUST 先判断段原文在去掉已定事件名、已解析数量和记一笔套话之后是否还有明细。没有剩余描述时，备注 MUST 为空字符串。此时系统 MUST NOT 查询备注飞轮，MUST NOT 调用备注模型，也 MUST NOT 把空备注写入飞轮。仍有描述时 MUST 保持先飞轮、再模型的顺序。别名已经带备注时 MUST 保持跳过模型。

#### Scenario: Quantity-only create has no remark

- **WHEN** 用户说「吃了120配方奶」，事件为配方奶，数量为 120
- **THEN** 备注 MUST 为空
- **AND** MUST NOT 调用备注抽取模型

#### Scenario: Leftover description still uses the remark path

- **WHEN** 用户说「吃了120配方奶有点凉」，事件为配方奶
- **THEN** 系统 MUST 继续备注飞轮，未命中再调用备注模型

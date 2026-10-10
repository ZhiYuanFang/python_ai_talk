## ADDED Requirements

### Requirement: 禁止整句整包意图向量回放
系统 MUST NOT 使用「用户整句 embedding 近邻 → 回放缓存的完整多事件意图并免确认执行」作为喂养意图匹配主策略。向量匹配若存在，MUST 仅用于段级 **事件身份**（短说法库），MUST NOT 单独决定 quantity/time/op 整包。

#### Scenario: 复合句不因近邻整包落库
- **WHEN** 用户输入「换尿布了，洗澡了，吃了120奶，睡觉了」
- **AND** 库中存在短说法或历史文档与「换尿布…拉臭臭」相近
- **THEN** 系统 SHALL NOT 仅据此免确认写入单条拉屎（或单条换尿布叶子）并忽略其它并列事件

## REMOVED Requirements

### Requirement: 系统使用向量相似度进行喂养事件匹配
**Reason**: 事件名/整句意图向量匹配已由段级短说法事件维与多维拼装替代；基线该条易被理解为整句短路。
**Migration**: 见 `intent-event-phrase-flywheel` 与 `intent-segment-multidim`。

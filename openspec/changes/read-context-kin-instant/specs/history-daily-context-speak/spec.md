## ADDED Requirements

### Requirement: Daily non-count history SHALL answer by utterance context

When a read-record turn uses daily history mode and the utterance is not a count question (几次 or 多少次), the system MUST NOT return the raw local summary plus flow lines as the user-facing answer. The system SHALL select a preset context strategy when the utterance matches one: food-list contexts (吃了哪些 or 吃了什么) MUST answer with food or remark names only; amount contexts (喝了多少) MUST answer with an aggregated quantity only; comparison contexts (和昨天比 or 比昨天) MUST answer with adjacent-day deltas only and MUST NOT append the flow. Count questions MUST keep the existing spoken count sentence.

#### Scenario: Food list does not dump flow

- **WHEN** 用户问这周吃了哪些辅食且进入日汇总查史且有记录
- **THEN** 用户回答 MUST 列出吃过的内容或备注
- **AND** MUST NOT 以本地摘要标题加逐日流水作为整段回答

#### Scenario: Count question unchanged

- **WHEN** 用户问昨天吃了几次辅食且进入日汇总查史
- **THEN** 系统 SHALL 仍以次数句作答
- **AND** MUST NOT 改为食物列表或模型自由发挥

### Requirement: Uncovered daily context SHALL use LLM and a rule gap

When daily non-count mode does not match a preset context strategy, the system MUST produce the user answer with an LLM grounded on the compact history and the utterance, MUST NOT invent records absent from that history, and MUST record a rule gap in a history-speak context dimension distinct from the miss inbox. The gap record MUST include the utterance so a later rule can cover that context.

#### Scenario: Unknown daily phrasing records a gap

- **WHEN** 日汇总非次数问对不上吃了哪些、喝了多少、和昨天比等预设语境
- **THEN** 系统 SHALL 用模型基于紧凑历史作答
- **AND** MUST 写入规则缺口且维度不是覆盖缺口

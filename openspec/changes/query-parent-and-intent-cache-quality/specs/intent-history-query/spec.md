## ADDED Requirements

### Requirement: 查记录确认话术必须点出事件名
当查记录需要用户确认时，`confirm_message` SHALL 由 Python 根据字典解析出的事件名生成，MUST 包含该名称（叶子或父）。系统 MUST NOT 使用「该事件」等不含具体名称的兜底。有 `event_id` 但名为空时 MUST 回查事件字典补名。

#### Scenario: Leaf history confirm names the event
- **WHEN** 用户问「上一次尿尿是什么时候」且分类给出尿尿
- **AND** 需要确认
- **THEN** `confirm_message` SHALL 含「尿尿」
- **AND** SHALL NOT 仅为「请确认是否查询该事件的历史？」

#### Scenario: Parent history confirm names the parent
- **WHEN** 用户问「上一次换尿布是什么时候」且分类给出父事件换尿布
- **AND** 需要确认
- **THEN** `confirm_message` SHALL 含「换尿布」

### Requirement: 查父展开子孙叶子并播报最近一条
当点查的已定事件为父事件时，系统 SHALL 递归收集其全部子孙叶子（不只直接子节点），按这些叶子 id 一次 filter 拉史，取 `startTime` 离现在最近的一条作为结果。`content` SHALL 同时点出父名与该叶子名。若无记录 SHALL 说明没有记到该父相关记录。本条 MUST NOT 改变用户显式点名多件叶子的「分别」播报。

#### Scenario: Last diaper is the latest among pee and poop
- **WHEN** 用户确认查询「换尿布」
- **AND** 叶子为尿尿与拉屎
- **AND** 最近一条是今天 14:11 的尿尿（一次性）
- **THEN** `content` SHALL 表明上一次换尿布的时候是尿尿，并使用相对时间（如今天 14:11）
- **AND** SHALL NOT 分别列出尿尿与拉屎各一条

#### Scenario: Nested parent expands to true leaves
- **WHEN** 父事件下仍有父节点
- **THEN** 拉史所用 `event_ids` SHALL 为递归得到的叶子 id
- **AND** SHALL NOT 只用直接子节点（若直接子仍为父）

#### Scenario: Explicit multi-leaf still reported separately
- **WHEN** 用户问「上一次睡觉拉屎分别在什么时候」且分类给出两个叶子 id
- **THEN** `content` SHALL 分别给出两事件最近时间
- **AND** SHALL NOT 塌成只报最近的一件

### Requirement: 点查模板按一次性计时计数区分
点查（非日汇总）播报 SHALL 按事件字典 `event_type`（`one|time|number`）使用模板，时间口吻保持相对时间（刚刚 / N分钟前 / 今天 HH:mm 等）。一次性 MUST NOT 带 number。计时已结束 MUST 带用时（时分）。计时无有效 `endTime` MUST 说明开始相对时间且现在正在进行中。计数 MUST 说「数量为：」后接数值；空或缺失 SHALL 视为 0。日汇总路径 MUST NOT 因本条改写。

#### Scenario: One-shot leaf has no quantity
- **WHEN** 点查一次性叶子且有记录
- **THEN** `content` SHALL 含事件名与相对时间
- **AND** SHALL NOT 包含数量为或 eventNumber

#### Scenario: Timer in progress
- **WHEN** 点查计时叶子且记录无有效结束时间
- **THEN** `content` SHALL 说明该相对时间开始的，现在正在进行中

#### Scenario: Count zero still spoken
- **WHEN** 点查计数叶子且 eventNumber 为空或 0
- **THEN** `content` SHALL 包含「数量为：0」

## ADDED Requirements

### Requirement: 分类提示注入全量树且 read 可输出父 id
`classify_intent` 的系统提示 SHALL 注入全量事件树（含父），并标明每项为父或叶子及从属关系。create/update/delete MUST 只使用叶子 id。read 当用户说的是父名时 MUST 输出该父 id，MUST NOT 由模型自行展开为多个叶子 id。执行查记录时再递归展开叶子。

#### Scenario: Prompt lists parent names
- **WHEN** 构建意图分类系统提示且字典中存在父事件「换尿布」及其叶子
- **THEN** 提示中 SHALL 出现换尿布为父及叶子名称
- **AND** SHALL 仍列出叶子供记事件匹配

#### Scenario: Read of parent outputs parent id
- **WHEN** 用户问「上一次换尿布是什么时候」且分类成功
- **THEN** 分类结果的 `event_id` 或 `event_ids` SHALL 含换尿布的父 id
- **AND** SHALL NOT 仅输出尿尿或拉屎之一而不含父 id

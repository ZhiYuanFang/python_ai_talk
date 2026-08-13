## ADDED Requirements

### Requirement: 分类须拆分复合切换句且每件自带动作
`classify_intent` 的系统提示 SHALL 要求：当用户一句话同时表达停止一件已有叶子并开始/记录另一件（如「不 X 了改 Y」「换成」「现在不…了」）时，MUST 输出 `events[]` 至少两项，每项 MUST 自带 `action` 与字典叶子 `event_id`/`event_name`。停止项 MUST 为 `action=end`；开始或记录项 MUST 为 `action=start` 或 `action=one`。系统 MUST NOT 把停止与开始揉成同一子项，MUST NOT 把两件都标成 `one` 或 `start`。顶层 `action` SHALL 为 `multi`。系统 MUST NOT 在分类前提示中注入本设备进行中历史摘要。

#### Scenario: 不爬了改坐了拆成 end 与 start
- **WHEN** 字典含叶子「爬练习」「坐练习」，用户输入「现在不爬了，改坐了」且分类成功
- **THEN** `events[]` SHALL 含一项 `action=end` 且事件为爬练习
- **AND** SHALL 含另一项 `action=start` 或 `action=one` 且事件为坐练习
- **AND** SHALL NOT 仅输出一件或两件均为 `one`/`start`

#### Scenario: 分类不注入进行中摘要
- **WHEN** 构建设备已有「爬练习」进行中记录时的分类系统提示
- **THEN** 提示 SHALL NOT 包含该进行中记录的摘要或 history id
- **AND** SHALL 仍列出字典中的爬练习与坐练习供匹配

### Requirement: 分类提示须提示同音并禁止发明事件
分类系统提示 SHALL 说明用户原文可能同音不同字，须对照可用事件表选择语义最接近的字典真名再填 id（例如怕≈爬、做≈坐、该≈改）。对不上字典时 MUST 列入 `missing_events` 或改为 conversation，MUST NOT 编造不在列表中的事件名或 id。偶发未能纠正错别字时，系统 MAY 走闲聊或确认失败，MUST NOT 为此注入进行中历史。

#### Scenario: 同音句仍应对字典真名
- **WHEN** 字典含「爬练习」「坐练习」，用户输入「现在不怕了，该做了」且模型按提示纠正成功
- **THEN** `events[]` SHALL 使用爬练习与坐练习的字典 id 与真名
- **AND** SHALL NOT 使用「怕练习」等列表外名称作为 `event_name`

### Requirement: 分类提示叶子可带字典类型且不得采信模型返回的类型
分类提示中的叶子条目 MAY 带字典 `type`（`one|time|number`），仅供模型选择 `start`/`end`/`one`。系统 MUST NOT 把 LLM 返回的 `event_type` 作为落库或计时判定依据。计时与否 MUST 在后续组装 batch 时按事件字典该叶子的 `event_type` 决定。

#### Scenario: 提示可含 type 但不采用模型类型
- **WHEN** 字典中爬练习 `event_type=time`、某一次性事件 `event_type=one`
- **THEN** 分类提示 MAY 在对应叶子上标明 type
- **AND** 即使模型 JSON 含 `event_type`，后续落库 MUST 仍以字典为准

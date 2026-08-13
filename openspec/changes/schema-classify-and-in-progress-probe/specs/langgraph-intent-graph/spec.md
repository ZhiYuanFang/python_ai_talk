## MODIFIED Requirements

### Requirement: 分类须拆分复合切换句且每件自带动作
当分类成功且用户一句话同时要停止一件已有叶子并开始/记录另一件时，结果 MUST 输出 `events[]` 至少两项，每项 MUST 自带 `action` 与字典叶子 id/名。停止项 MUST 为 `action=end`；另一项 MUST 为 `start` 或 `one`。系统 MUST NOT 把停止与开始揉成同一子项。顶层 `action` SHALL 为 `multi`。分类系统提示 MUST 用 `events[]` 的字段含义表达「一句话多件、每件自己的 action」，MUST NOT 罗列用户句式模板（如「不 X 了改 Y」）。缓存未命中时，分类前提示 MUST 注入本设备进行中计时摘要（见进行中探针要求）。

#### Scenario: 不爬了改坐了拆成 end 与 start
- **WHEN** 字典含叶子「爬练习」「坐练习」，用户输入「现在不爬了，改坐了」且分类成功
- **THEN** `events[]` SHALL 含一项 `action=end` 且事件为爬练习
- **AND** SHALL 含另一项 `action=start` 或 `action=one` 且事件为坐练习
- **AND** SHALL NOT 仅输出一件或两件均为 `one`/`start`

#### Scenario: 分类注入进行中摘要
- **WHEN** 构建设备已有「爬练习」进行中计时记录且缓存未命中时的分类系统提示
- **THEN** 提示 SHALL 出现爬练习为进行中及该叶子字典 id
- **AND** SHALL NOT 包含该条记录的 history id

## ADDED Requirements

### Requirement: 分类提示仅描述字段含义与表约束
`classify_intent` 的系统提示 SHALL 说明各 JSON 字段含义（`op`/`action`/`events`/`event_ids`/`start_time`/`end_time`/`remark_keyword`/`missing_events` 等）以及只能使用事件表中的 id 与 name。`op` 的说明 MUST 按语义区分 create / read / update / delete，MUST NOT 用用户口头关键字或例句把某类话术绑定到某个 `op`（包括不得写「上次/上一次/什么时候」即 read）。系统 MUST NOT 在提示中维护同音对照表或句式清单。

#### Scenario: 提示不含上一次即查询
- **WHEN** 构建分类系统提示
- **THEN** 提示 SHALL 包含 `op=read` 与 `op=delete` 的字段含义
- **AND** SHALL NOT 出现将「上一次」或「什么时候」指定为 read 的规则句

#### Scenario: 删除上一次由字段含义区分
- **WHEN** 用户输入「删除上一次坐练习的记录」且分类成功、字典含坐练习
- **THEN** 结果 `op` SHALL 为 `delete`
- **AND** SHALL NOT 为 `read`

### Requirement: 分类前注入进行中计时摘要
当意图缓存未命中时，系统 SHALL 在分类前拉取近窗历史，筛出 `endTime` 为空或 0 且字典 `event_type` 为 `time` 的叶子，将名称、字典 id 与开始时间作为一行摘要注入分类提示。无此类记录时 MUST 明确写无进行中计时。摘要 MUST NOT 包含历史行 id。`action=end` 的 batch 项仍 MUST 只带叶子 `eventId`，MUST NOT 因探针填写 `history_id`。

#### Scenario: 有进行中则写入提示
- **WHEN** 缓存未命中且近窗存在爬练习进行中（计时、无结束时间）
- **THEN** 分类提示 SHALL 含爬练习及其字典 id
- **AND** SHALL NOT 含该历史行主键

#### Scenario: 无进行中也说明
- **WHEN** 缓存未命中且近窗无进行中计时
- **THEN** 分类提示 SHALL 表明当前无进行中计时

## REMOVED Requirements

### Requirement: 分类提示须提示同音并禁止发明事件
**Reason**: 同音对照表仍是话术补丁；禁止编造事件已由「只用表内 id/name」约束覆盖。同音靠进行中名单与模型语义，不靠怕≈爬。
**Migration**: 使用本文件「分类提示仅描述字段含义与表约束」与「分类前注入进行中计时摘要」。

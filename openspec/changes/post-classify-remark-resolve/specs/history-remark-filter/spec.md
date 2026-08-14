## MODIFIED Requirements

### Requirement: 字典外词经备注探针定为已知事件
当用户所说名称经字典匹配（含简称/进行态对应）仍无法落到表内事件时，系统 MUST NOT 将其当作新事件类型。系统 SHALL 在**意图分类完成之后**，将该名称作为 `remark` 调用兄弟仓 filter（本设备、建议近窗、小 limit、空 `eventIds`）做备注反查，按命中行的事件聚合，再写入字典 `event_id` 与 `remark_keyword`。系统 MUST NOT 在分类前做备注探针，MUST NOT 把备注探针摘要或原始历史行注入分类 prompt。系统 MUST NOT 用本地查询句正则决定是否反查或是否为 read。系统 MUST NOT 用常识将表外专名改写成某字典类别事件后再跳过反查（实现上：字典未命中才反查；提示亦禁止专名升格）。

#### Scenario: 上一次吃的 AD
- **WHEN** 用户问「上一次什么时候吃的 AD」且分类将事件名保留为 AD（或等价字典外专名），近窗备注含 AD 的记录均落在营养品
- **THEN** 备注反查后结果 SHALL 使用字典名「营养品」与对应 `event_id`，且 `remark_keyword` 为 AD
- **AND** 确认文案 SHALL 询问是否查询上一次吃的营养品（按备注 AD）
- **AND** 确认前 MUST NOT 把全类型原始 history 注入分类 prompt
- **AND** 确认后正式 filter SHALL 带营养品 `eventIds` 与 `remark=AD`

#### Scenario: 多命中消歧
- **WHEN** 备注反查命中两个及以上不同字典叶子（例如营养品与药品均含备注 AD）
- **THEN** 系统 SHALL 发起消歧，选项为这些叶子的字典名
- **AND** SHALL NOT 静默选取出现次数最多的叶子
- **AND** 消歧完成前 MUST NOT 正式拉史或落库

#### Scenario: 零命中无法识别
- **WHEN** 备注反查近窗无命中（含用户首次说「记一下 AD」且历史备注从未出现 AD）
- **THEN** 系统 SHALL 反馈无法识别对应的事件
- **AND** MUST NOT 设置 `is_new_event` 并创建 AD 事件类型
- **AND** MUST NOT 用常识猜测「营养品」等字典事件并进入可落库确认

#### Scenario: 光说 AD 先分类再反查
- **WHEN** 用户只说「AD」且无 pending
- **THEN** 系统 SHALL 先由分类决定 `op`（记录或查询等）
- **AND** 因 AD 不在字典，SHALL 走分类后备注反查
- **AND** SHALL NOT 直接建新事件或拉全量史
- **AND** SHALL NOT 在分类前因缺少「上一次」等字样而跳过反查路径的可用性（反查触发条件是字典未命中，不是查询句式）

## ADDED Requirements

### Requirement: 表内活动简称与进行态须优先字典匹配
在备注反查之前，系统 SHALL 尝试将用户或分类给出的名称匹配到事件字典：精确名、互相包含，以及对常见进行态前缀（如「正在」「在」）剥离后再包含匹配。匹配成功时 MUST 使用字典真名与 id，MUST NOT 再对该名称做备注反查。

#### Scenario: 正在爬对应爬练习
- **WHEN** 字典含叶子「爬练习」，用户输入含「正在爬」且分类成功或规则匹配成功
- **THEN** 结果 SHALL 使用事件「爬练习」及其 `event_id`
- **AND** 本轮 MUST NOT 仅因字面「正在爬」不在表内而调用备注反查
- **AND** MUST NOT 将「正在爬」列为无法识别

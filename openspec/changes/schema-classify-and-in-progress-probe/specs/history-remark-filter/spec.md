## MODIFIED Requirements

### Requirement: 字典外词经备注探针定为已知事件
当用户词不在事件字典时，系统 MUST NOT 将其当作新事件类型。系统 SHALL 尝试抽出字典外专名；抽出成功后用备注探针（小 limit）按设备历史聚合命中事件，只把一行摘要注入分类（不得注入原始行列表），再由分类输出字典 `event_id` 与 `remark_keyword`，并确认后正式拉史。系统 MUST NOT 用本地查询句正则（如匹配「上一次」）决定是否做备注探针或是否为 read。

#### Scenario: 上一次吃的 AD
- **WHEN** 用户问「上一次什么时候吃的 AD」且近窗备注含 AD 的记录均落在营养品
- **THEN** 分类或确认话术 SHALL 使用字典名「营养品」而非事件名「AD」
- **AND** 确认文案 SHALL 询问是否查询上一次吃的营养品（按备注 AD）
- **AND** 确认前 MUST NOT 把全类型原始 history 注入分类 prompt
- **AND** 确认后正式 filter SHALL 带营养品 `eventIds` 与 `remark=AD`

#### Scenario: 探针零命中仍禁止新建事件
- **WHEN** 备注探针无命中
- **THEN** 系统 MAY 用常识给出候选字典事件并确认
- **AND** MUST NOT 设置 `is_new_event` 并创建 AD 事件类型
- **AND** 确认后正式查询仍无行时 `content` SHALL 说明最近没有备注里带该词的对应事件

#### Scenario: 光说 AD 先分读写
- **WHEN** 用户只说「AD」且无 pending
- **THEN** 系统 SHALL 由分类决定是记录还是查询并确认
- **AND** SHALL NOT 直接建新事件或拉全量史
- **AND** SHALL NOT 仅因句子不含「上一次」而跳过备注探针（有字典外词仍可探针）

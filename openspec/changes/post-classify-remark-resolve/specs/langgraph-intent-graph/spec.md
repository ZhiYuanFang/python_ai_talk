## MODIFIED Requirements

### Requirement: intent_graph 状态图结构
系统 SHALL 使用 LangGraph StateGraph 构建意图分析流程图（intent_graph），包含意图缓存匹配、分类前进行中计时探针、意图分类、**分类后备注反查**（字典未命中时）、条件路由、批量历史 CRUD 与查记录模板播报。图 MUST NOT 在分类前做备注探针或注入备注摘要。图 MUST NOT 包含 `match_event_by_vector` 节点，MUST NOT 包含 `call_clinic_agent` 节点，MUST NOT 包含 `judge_data_requirement` 或历史答题 LLM 节点，MUST NOT 从 `feeding` 导入 `clinic` 图。

#### Scenario: intent_graph 节点组成
- **WHEN** 构建 intent_graph
- **THEN** 图 SHALL 包含意图缓存匹配、classify_intent，以及批量执行 CRUD / 拉史模板播报（名称以实现为准）
- **AND** 图 SHALL 在缓存未命中时于分类前注入进行中计时摘要（节点名以实现为准）
- **AND** 图 SHALL 在分类后对字典未命中名称具备备注反查步骤（独立节点或分类后继节点）
- **AND** 图 SHALL NOT 在分类前注册仅用于备注 OOV 探针的步骤，SHALL NOT 将备注探针摘要写入分类系统提示
- **AND** 图 SHALL 包含条件边，根据缓存命中、确认需求与 `op`/`target_type` 路由
- **AND** 图 SHALL NOT 注册 `match_event_by_vector`、`call_clinic_agent` 或历史答题 LLM

#### Scenario: feeding 意图执行落库
- **WHEN** 分类或缓存结果为 create/update/delete 且无需确认
- **THEN** 图 SHALL 在 Python 侧执行 history HTTP 后结束
- **AND** SHALL NOT 把未执行结构交给 Go 写库

#### Scenario: history 意图路由
- **WHEN** 分类结果为查记录（`op=read` 或 `target_type=history`）
- **THEN** 图 SHALL 按已定事件拉史并用模板填写 `content` 后结束
- **AND** SHALL NOT 进入 clinic_graph
- **AND** SHALL NOT 调用历史答题 LLM

#### Scenario: conversation 意图路由
- **WHEN** classify_intent 返回 target_type=conversation
- **THEN** 图 SHALL 结束并带短回复 `content`
- **AND** SHALL NOT 调用 clinic agent

#### Scenario: exit 意图路由
- **WHEN** classify_intent 返回 target_type=exit
- **THEN** 图 SHALL 直接返回 IntentResponse，不执行落库

#### Scenario: 不再路由 suggest
- **WHEN** 用户输入成长建议类闲聊
- **THEN** 意图图 MAY 将其归为 conversation
- **AND** SHALL NOT 再进入 suggest + clinic 分支

### Requirement: 分类提示仅描述字段含义与表约束
`classify_intent` 的系统提示 SHALL 说明各 JSON 字段含义（`op`/`action`/`events`/`event_ids`/`start_time`/`end_time`/`remark_keyword`/`missing_events` 等）以及事件表约束。`op` 的说明 MUST 按语义区分 create / read / update / delete，MUST NOT 用用户口头关键字或例句把某类话术绑定到某个 `op`（包括不得写「上次/上一次/什么时候」即 read）。系统 MUST NOT 在提示中维护同音对照表或句式清单。系统提示 MUST 说明：表内已有活动的简称或进行状态须对到表内真名与 id；表中不存在的专名/代号不得凭常识改写成某类别事件，应保留用户词且 `event_id` 为空。系统提示 MUST NOT 注入备注探针摘要。

#### Scenario: 提示不含上一次即查询
- **WHEN** 构建分类系统提示
- **THEN** 提示 SHALL 包含 `op=read` 与 `op=delete` 的字段含义
- **AND** SHALL NOT 出现将「上一次」或「什么时候」指定为 read 的规则句

#### Scenario: 删除上一次由字段含义区分
- **WHEN** 用户输入「删除上一次坐练习的记录」且分类成功、字典含坐练习
- **THEN** 结果 `op` SHALL 为 `delete`
- **AND** SHALL NOT 为 `read`

#### Scenario: 提示区分简称与专名升格
- **WHEN** 构建分类系统提示
- **THEN** 提示 SHALL 要求将表内活动的进行态/简称对到表内真名（例如正在爬对应爬练习）
- **AND** SHALL 禁止将表外专名凭常识改写成类别事件
- **AND** SHALL NOT 包含「备注探针摘要」类注入块

### Requirement: 分类前注入进行中计时摘要
当意图缓存未命中时，系统 SHALL 在分类前拉取近窗历史，筛出 `endTime` 为空或 0 且字典 `event_type` 为 `time` 的叶子，将名称、字典 id 与开始时间作为一行摘要注入分类提示。无此类记录时 MUST 明确写无进行中计时。摘要 MUST NOT 包含历史行 id。`action=end` 的 batch 项仍 MUST 只带叶子 `eventId`，MUST NOT 因探针填写 `history_id`。本要求 MUST NOT 被解释为允许分类前备注探针。

#### Scenario: 有进行中则写入提示
- **WHEN** 缓存未命中且近窗存在爬练习进行中（计时、无结束时间）
- **THEN** 分类提示 SHALL 含爬练习及其字典 id
- **AND** SHALL NOT 含该历史行主键

#### Scenario: 无进行中也说明
- **WHEN** 缓存未命中且近窗无进行中计时
- **THEN** 分类提示 SHALL 表明当前无进行中计时

#### Scenario: 分类提示无备注探针摘要
- **WHEN** 缓存未命中且用户输入含字典外专名
- **THEN** 分类系统提示 SHALL NOT 包含「备注探针摘要」或等价备注命中聚合旁白

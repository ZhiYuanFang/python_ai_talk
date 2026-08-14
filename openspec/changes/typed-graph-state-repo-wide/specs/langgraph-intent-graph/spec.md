## MODIFIED Requirements

### Requirement: intent_graph 状态图结构
系统 SHALL 使用 LangGraph StateGraph 构建意图分析流程图（intent_graph），包含意图缓存匹配、分类前进行中计时探针、意图分类、分类后备注反查（字典未命中时）、条件路由、批量历史 CRUD 与查记录模板播报。图的 State MUST 为 Pydantic 模型。图 MUST NOT 在分类前做备注探针或注入备注摘要。图 MUST NOT 包含 `match_event_by_vector` 节点，MUST NOT 包含 `call_clinic_agent` 节点，MUST NOT 包含 `judge_data_requirement` 或历史答题 LLM 节点，MUST NOT 从 `feeding` 导入 `clinic` 图。

#### Scenario: intent_graph 节点组成
- **WHEN** 构建 intent_graph
- **THEN** 图 SHALL 包含意图缓存匹配、classify_intent，以及批量执行 CRUD / 拉史模板播报（名称以实现为准）
- **AND** 图 SHALL 在缓存未命中时于分类前注入进行中计时摘要（节点名以实现为准）
- **AND** 图 SHALL 在分类后对字典未命中名称具备备注反查步骤（独立节点或分类后继节点）
- **AND** 图 SHALL NOT 在分类前注册仅用于备注 OOV 探针的步骤，SHALL NOT 将备注探针摘要写入分类系统提示
- **AND** 图 SHALL 包含条件边，根据缓存命中、确认需求与 `op`/`target_type` 路由
- **AND** 图 SHALL NOT 注册 `match_event_by_vector`、`call_clinic_agent` 或历史答题 LLM
- **AND** StateGraph 注册的 State 类型 SHALL 为 Pydantic 意图 State

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

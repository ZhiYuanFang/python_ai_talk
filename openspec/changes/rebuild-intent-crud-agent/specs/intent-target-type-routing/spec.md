## MODIFIED Requirements

### Requirement: classify 后按 target_type 路由
`classify_intent` 完成后，意图图 SHALL 根据操作与 `intent_result.target_type` 进入对应后处理，不得一律 END，也不得将 history/conversation 送入 clinic agent。

#### Scenario: feeding 进入确认或执行
- **WHEN** 分类结果为喂养 CRUD（含多事件）
- **THEN** 下一节点 SHALL 为确认 pending 或 Python 历史执行（以实现分支为准）
- **AND** SHALL NOT 为 `call_clinic_agent`

#### Scenario: history 进入意图图内拉史
- **WHEN** 分类结果 `target_type` 为 `history` 或 `op=read`
- **THEN** 图 SHALL 执行拉史与生成回答后结束
- **AND** SHALL NOT 将下一节点设为 `call_clinic_agent`

#### Scenario: conversation 直接结束
- **WHEN** 分类结果 `target_type` 为 `conversation`
- **THEN** 图 SHALL 结束并带 `content`
- **AND** SHALL NOT 进入 clinic agent

#### Scenario: exit 直接结束
- **WHEN** 分类结果 `target_type` 为 `exit`
- **THEN** 图 SHALL 结束且不进入确认或 clinic

### Requirement: 向量中置信仍走确认
单一 create 的事件名向量匹配在需要确认的置信度区间时 SHALL 设置 `need_confirm` 并结束本轮等待续聊，SHALL NOT 写库。复合多事件句 MUST NOT 走该单事件确认快路径。

#### Scenario: 中置信单事件 create 触发确认
- **WHEN** 单一 create 向量匹配设置 `need_confirm=True`
- **THEN** 响应 SHALL 带确认话术与 `conversation_id`
- **AND** 本轮 MUST NOT 调用 history add

## REMOVED Requirements

### Requirement: 保留 clinic 调用后的 target_type
**Reason**: 意图图不再调用 `call_clinic_agent`，无需保留 clinic 合并后的 suggest 类型。
**Migration**: 成长建议改走 `POST /v1/clinic`；意图 conversation 不进入 clinic。

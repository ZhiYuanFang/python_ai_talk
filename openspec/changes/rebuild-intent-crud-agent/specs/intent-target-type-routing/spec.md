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

## REMOVED Requirements

### Requirement: 向量中置信仍走确认
**Reason**: 事件名向量匹配已删除，不再有中置信单事件快路径。
**Migration**: 缓存 miss 的 create 由分类默认 `need_confirm`。

### Requirement: 保留 clinic 调用后的 target_type
**Reason**: 意图图不再调用 `call_clinic_agent`，无需保留 clinic 合并后的 suggest 类型。
**Migration**: 成长建议改走 `POST /v1/clinic`；意图 conversation 不进入 clinic。

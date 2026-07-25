## ADDED Requirements

### Requirement: classify 后按 target_type 路由
`classify_intent` 完成后，意图图 SHALL 根据 `intent_result.target_type` 进入对应后处理，不得一律 END。

#### Scenario: feeding 进入确认
- **WHEN** 分类结果 `target_type` 为 `feeding`（含多事件）
- **THEN** 下一节点 SHALL 为 `prepare_confirm`

#### Scenario: history 进入历史短链
- **WHEN** 分类结果 `target_type` 为 `history`
- **THEN** 图 SHALL 执行 `judge_data_requirement → fetch_history → generate_response`（或等价顺序的已注册节点链）后结束

#### Scenario: conversation 与 suggest 进入 clinic agent
- **WHEN** 分类结果 `target_type` 为 `conversation` 或 `suggest`
- **THEN** 下一节点 SHALL 为 `call_clinic_agent`

#### Scenario: exit 直接结束
- **WHEN** 分类结果 `target_type` 为 `exit`
- **THEN** 图 SHALL 结束且不进入确认或 clinic

### Requirement: 保留 clinic 调用后的 target_type
`call_clinic_agent` 合并结果时 SHALL 保留进入该节点前的 `intent_result.target_type`（除非产品明确要求改写），不得无条件改写为 `conversation` 导致 suggest 语义丢失。

#### Scenario: suggest 调用 clinic 后仍为 suggest
- **WHEN** 进入 `call_clinic_agent` 前 `target_type` 为 `suggest` 且执行成功
- **THEN** 最终状态中的 `intent_result.target_type` SHALL 仍为 `suggest`
- **AND** 回答内容 SHALL 可供路由填入响应 `content`

### Requirement: 向量中置信仍走确认
向量匹配在需要确认的置信度区间时 SHALL 继续路由到 `prepare_confirm`，与 LLM feeding 确认路径共用真实确认节点。

#### Scenario: 中置信向量匹配触发确认
- **WHEN** 向量匹配设置 `need_confirm=True`
- **THEN** 图 SHALL 进入真实 `prepare_confirm` 并 interrupt

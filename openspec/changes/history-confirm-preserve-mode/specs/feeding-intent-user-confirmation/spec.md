## ADDED Requirements

### Requirement: 查史 pending 须持久化 history_mode 与 limit
创建查史相关待确认会话（含 `create_history_confirm_response` 叶子/父软确认，以及查史场景下的父消歧 pending）时，系统 MUST 将当前意图中的 `history_mode`（若为 `point` 或 `daily`）与可选 `limit` 写入 pending。用户确认或消歧选中后拼执行字段时，MUST 从 pending 回填上述字段（查父确认拼 fields 分支不得遗漏）。

#### Scenario: 查史软确认 pending 带上 daily
- **WHEN** 图后处理对 `target_type=history` 且 `need_confirm` 调用查史软确认
- **AND** 意图含 `history_mode=daily`
- **THEN** 所建 pending 的 `history_mode` SHALL 为 `daily`
- **AND** 若意图含 `limit`，pending SHALL 保留该 `limit`

#### Scenario: 确认回填不丢 mode
- **WHEN** 用户对已持久化 `history_mode=daily` 的查史 pending 确认通过
- **THEN** 交给播报/执行的意图字段 SHALL 含 `history_mode=daily`

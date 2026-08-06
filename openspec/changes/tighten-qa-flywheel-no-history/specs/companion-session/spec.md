## ADDED Requirements

### Requirement: Persist history grounding and QA match on last_suggestion
系统在 clinic（及共用 append 的 intent clinic 路径）成功写入 `last_suggestion` 时，SHALL 持久化：

- `history_grounded`：本轮回答是否按需要喂养史路径生成（`needs_history=true` 或强制拉史为 true）；缺省读取时若缺失则按 true 处理（保守，阻止误 promote）。
- `qa_match_id`：若本轮为 Q&A 捷径命中，则为命中条目 id；否则为空。

既有字段（`standalone_question`、`age_band`、`knowledge_ids` 等）保持兼容。

#### Scenario: No-history clinic turn records history_grounded false
- **WHEN** clinic 本轮 `needs_history` 为 false 且未强制拉史并成功 append_turn
- **THEN** `last_suggestion.history_grounded` SHALL 为 false

#### Scenario: QA hit records qa_match_id
- **WHEN** clinic 本轮 Q&A 捷径命中并成功 append_turn
- **THEN** `last_suggestion.qa_match_id` SHALL 等于命中条目 id

#### Scenario: Legacy session missing fields is conservative for promote
- **WHEN** 读回的 `last_suggestion` 无 `history_grounded` 字段
- **THEN** promote 逻辑 SHALL 视为已接地（不入库）

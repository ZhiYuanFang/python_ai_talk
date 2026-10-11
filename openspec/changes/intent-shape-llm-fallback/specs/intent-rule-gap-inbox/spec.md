## ADDED Requirements

### Requirement: 形态维 LLM 兜底须标记 llm_used
当形态维因计时开/关暧昧调用 SHAPE 小 LLM 时，系统 SHALL 写入 `dimension=shape`（或等价）的缺口记录，且 MUST 含 `llm_used=true`，MAY 含 `llm_result` 摘要。

#### Scenario: SHAPE 兜底记缺口
- **WHEN** 系统对某段调用 SHAPE 小 LLM
- **THEN** 缺口收件箱 SHALL 有对应 shape 维记录且 `llm_used` 为真

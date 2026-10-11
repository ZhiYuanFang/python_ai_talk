## MODIFIED Requirements

### Requirement: 相似度门槛 0.72
事件维向量检索采纳 MUST 要求相似度分数 ≥ **0.72**；低于该值 SHALL 视为未命中，并继续 EVENT 阶梯后续步骤（含 Go 备注反查与事件小 LLM 兜底）；若仍无稳定 `event_id` 则失败重说。MUST NOT 在分数不足时直接采用 Top-1 `event_id`。

#### Scenario: 分数不足
- **WHEN** Top-1 短说法 score &lt; 0.72
- **THEN** 系统 SHALL NOT 采用该条 event_id 作为高置信事件维结果
- **AND** SHALL 继续 Go 备注反查与（若仍未定）事件小 LLM，而非仅因低分立即终局失败

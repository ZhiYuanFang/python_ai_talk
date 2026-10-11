## MODIFIED Requirements

### Requirement: 非事件维规则缺口须落库
当类型、时间、数量或形态维出现规则未覆盖（含时间半命中、类型冲突/无线索而调用 LLM 兜底、数量规则 miss 后 LLM 兜底、number 叶缺量触发追问等）时，系统 SHALL 将缺口记录持久化到 Python 侧收件箱（非向量库）。记录 MUST 至少包含：`dimension`、`segment_text`、`utterance`、`reason`、`created_at`。凡实际调用了维级小 LLM 兜底，记录 MUST 含 `llm_used=true`，MAY 含 `llm_result` 摘要、`device_no`、`status`。

#### Scenario: 时间半命中写入缺口
- **WHEN** 时间维规则抽到钟点但仍有未消费日/段残留（半命中）
- **THEN** 系统 SHALL 写入一条 `dimension` 为时间类的缺口记录，含段原文与整句

#### Scenario: TYPE 兜底标记 llm_used
- **WHEN** 类型维因无线索调用 TYPE 小 LLM
- **THEN** 对应缺口记录 SHALL 含 `llm_used=true`

### Requirement: 事件维 miss 可记入缺口
当事件维词典、向量、Go 备注反查之后进入事件小 LLM，或最终导致段失败时，系统 SHALL 写入 `dimension=event`（或等价）的缺口记录，便于人工补短说法种子。进入事件小 LLM 时 MUST 标记 `llm_used=true`。

#### Scenario: 事件向量未过门槛
- **WHEN** 事件维 Top-1 score &lt; 0.72 且最终未得到稳定 event_id
- **THEN** 系统 SHALL 落一条事件维缺口记录

#### Scenario: 事件小 LLM 写入 llm_used
- **WHEN** Go 反查零命中后调用 EVENT 小 LLM
- **THEN** 缺口记录 SHALL 含 `llm_used=true`

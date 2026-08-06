## ADDED Requirements

### Requirement: Rejection blocks Q&A fast path for the current turn
当三态判定结果为 `rejected` 时，系统 SHALL 在本轮 clinic 状态中设置禁捷径信号（如 `block_fast_path=true`），使得本轮不得命中并返回全局 Q&A 缓存答案，MUST 继续完整数据准备与生成路径（除非其它既有结束条件）。`accepted`、`unclear` 或无待判定建议时，SHALL NOT 仅因此设置该禁捷径信号。

#### Scenario: Rejected sets block_fast_path
- **WHEN** 上一条建议待判定且本轮判定为 `rejected`
- **THEN** clinic state SHALL 携带禁捷径信号，且本轮 Q&A 检索/命中被跳过

#### Scenario: Unclear does not block fast path
- **WHEN** 判定为 `unclear`
- **THEN** 系统 SHALL NOT 仅因该判定设置禁捷径信号

### Requirement: Rejection demotes linked Q&A entry
当判定为 `rejected` 且上一条建议带有非空 `qa_match_id` 时，系统 SHALL 对该问答条目执行质量分下调；该行为可与通识 `knowledge_ids` 飞轮并存。

#### Scenario: Rejected QA answer demotes entry
- **WHEN** 判定为 `rejected` 且 `qa_match_id` 非空
- **THEN** 系统对该 id 执行负面质量更新且不中断主流程

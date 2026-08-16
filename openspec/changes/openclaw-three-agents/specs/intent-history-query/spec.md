## ADDED Requirements

### Requirement: 点查支持 top_k 条模板播报
当用户问「上次/前两次/什么时候」等点查且已定 `event_ids` 时，系统 SHALL 按 `top_k`（缺省 1，上限 ≤5）拉取并模板播报至多 k 条记录。`top_k=1` 时行为可与「最近一条」点查一致；`top_k>1` 时 MUST 分条给出时间（及用量/时长/备注若有）。系统 MUST NOT 在点查路径用空 `event_ids` 拉取全类型原始行并注入生成 LLM。

#### Scenario: 前两次点查
- **WHEN** 用户问「前两次喂奶分别在什么时候」且事件已确定、`top_k=2`
- **THEN** `content` SHALL 用模板给出至多两次的时间说明

#### Scenario: 点查禁止全事件原始行进 LLM
- **WHEN** 点查意图的 `event_ids` 为空且备注探针亦未定出事件
- **THEN** 系统 MUST NOT 将全类型原始史注入生成式答题 LLM

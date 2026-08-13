## MODIFIED Requirements

### Requirement: Query utterances must not vector-commit as feeding
当用户文本呈现历史查询意图（如询问上次/什么时候/分别/多少等）时，系统 SHALL NOT 将意图定为 feeding 落库；SHALL 将 `op` 定为 `read`（或 `target_type=history`）并在意图图内答题。

#### Scenario: Last poop time is not feeding
- **WHEN** 用户输入类似「上一次拉屎是什么时候」
- **THEN** 系统 SHALL 走查记录路径（分类或意图缓存）
- **AND** SHALL NOT 定为 feeding create
- **AND** SHALL NOT 进入 clinic agent

#### Scenario: Record utterance can still be feeding
- **WHEN** 用户输入类似「拉屎了」或「记录拉屎」且无查询句式
- **THEN** 系统仍 MAY 经意图缓存或分类得到 create

### Requirement: History intent routes to clinic agent
当意图分类结果为查记录（`history` / `op=read`）时，意图图 SHALL 在本图内按已定事件拉取历史并用模板填写 `content`，SHALL NOT 进入 `call_clinic_agent`，SHALL NOT 调用历史答题 LLM。

#### Scenario: History uses intent graph fetch
- **WHEN** 路由看到查记录意图
- **THEN** 下一节点 SHALL 为拉史与生成回答
- **AND** SHALL NOT 为 `call_clinic_agent`

### Requirement: Clinic answers factual last-event questions from history
当用户经 **clinic** 入口提问查记录类问题时，clinic 生成仍 SHALL 以喂养历史为准回答时间点；对「分别」类多事件问题 SHALL 分别给出各事件最近一次时间；无记录时 SHALL 明确说明没有记到。意图入口的查记录由意图图负责，不经本条 clinic 路径。

#### Scenario: Single last-event time via clinic
- **WHEN** 用户向 `/v1/clinic` 或 `/clinic/stream` 问某一事件上次时间且历史中有该事件
- **THEN** 回答 SHALL 基于该历史时间点而非臆造

## REMOVED Requirements

### Requirement: Pure history skips knowledge vector search
**Reason**: 该条约束的是 `call_clinic_agent` 处理 history 时跳过知识检索；意图 history 已不走 clinic。
**Migration**: 意图查记录图内默认不检索通识知识；clinic 入口自己的 needs_history/知识门控不变。

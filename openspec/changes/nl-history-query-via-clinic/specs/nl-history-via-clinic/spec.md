## ADDED Requirements

### Requirement: Query utterances must not vector-commit as feeding

当用户文本呈现历史查询意图（如询问上次/什么时候/分别/多少等）时，系统 SHALL NOT 因向量高置信直接将意图定为 feeding 落库；SHALL 降级至 LLM 意图分类（或等价非 feeding 路径）。

#### Scenario: Last poop time is not feeding

- **WHEN** 用户输入类似「上一次拉屎是什么时候」
- **THEN** 向量匹配阶段 SHALL NOT 以 feeding 高置信直接结束；后续分类 SHALL 倾向 history（或进入查记录的 clinic 路径）

#### Scenario: Record utterance can still be feeding

- **WHEN** 用户输入类似「拉屎了」或「记录拉屎」且无查询句式
- **THEN** 系统仍 MAY 经向量或分类得到 feeding

### Requirement: History intent routes to clinic agent

当意图分类结果为 `history` 时，意图图与 intent 流式步进 SHALL 进入 `call_clinic_agent`，SHALL NOT 再执行原 history 短链末端的 `generate_response` 路径。

#### Scenario: History uses call_clinic_agent

- **WHEN** `route_after_classify`（或流式等价路由）看到 `target_type=history`
- **THEN** 下一节点 SHALL 为 `call_clinic_agent`

### Requirement: Pure history skips knowledge vector search

当 `call_clinic_agent` 处理 `target_type=history` 时，数据准备 SHALL 跳过 `search_vectors`（knowledge 为空或不检索），仍 SHALL 拉取喂养历史以供答题。

#### Scenario: History clinic agent does not search knowledge

- **WHEN** intent 为 history 并执行 clinic 数据准备
- **THEN** 系统 SHALL NOT 对知识库执行向量检索；生成所用 knowledge 为空或未注入

#### Scenario: Suggest still may search knowledge

- **WHEN** intent 为 suggest 并执行 clinic 数据准备
- **THEN** 系统 MAY 仍执行 `search_vectors`

### Requirement: Clinic answers factual last-event questions from history

clinic 闺蜜生成在面对查记录类问题时，SHALL 以喂养历史为准回答时间点；对「分别」类多事件问题 SHALL 分别给出各事件最近一次时间；无记录时 SHALL 明确说明没有记到。

#### Scenario: Single last-event time

- **WHEN** 用户问某一事件上次时间且历史中有该事件
- **THEN** 回答 SHALL 包含可辨认的时间信息（来自记录，非编造）

#### Scenario: Multiple last-event times

- **WHEN** 用户问睡觉与拉屎上次分别何时且历史中两类均有记录
- **THEN** 回答 SHALL 分别覆盖两类事件的最近时间

### Requirement: History events in prompts are field-trimmed

向 LLM 注入喂养历史时，系统 SHALL 仅保留 eventName、eventNumber、startTime、endTime、remark 等约定字段（缺失则省略），SHALL NOT 把无关元数据整包塞入查记录/clinic 提示。

#### Scenario: Trimmed history JSON in clinic prompt

- **WHEN** clinic_answer（或共用裁剪函数）格式化 history_events
- **THEN** 每条记录仅含约定字段子集

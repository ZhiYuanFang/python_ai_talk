## Why

家长用自然语言查喂养记录（如「上一次拉屎是什么时候」「上一次睡觉拉屎分别在什么时候」）时，intent 向量匹配常因事件名命中而误判为 **feeding 落库**；即便走到 history，也与 clinic 陪聊能力分裂。产品选定方案 **A**：查记录统一走 clinic agent，并在纯 history 时跳过知识向量检索，准确答时间点且更省延迟。

## What Changes

- **向量门禁**：识别查询句式（何时/上次/分别/多少等）时，禁止高置信直接提交 feeding，降级 LLM 分类
- **分类提示强化**：问「上次/什么时候/分别」→ `history`，不得标 feeding
- **路由**：`history` → `call_clinic_agent`（不再走 `judge → fetch → generate_response` 短链）
- **clinic agent**：`target_type=history` 时设 `skip_knowledge`，数据准备跳过 `search_vectors`
- **clinic_answer**：查记录题按历史答时间（支持多事件「分别」）；放宽与「约 50 字」冲突的约束
- **data_requirement**：强化「上一次 / 分别」的 event_ids 与时间窗指引
- **（建议）** prompt 注入历史时裁剪字段为 eventName / eventNumber / startTime / endTime / remark
- 无对外 API **BREAKING**（intent/clinic 响应形状不变）

## Capabilities

### New Capabilities

- `nl-history-via-clinic`: 自然语言查记录经 clinic agent 答题，含查询门禁、history 路由、跳过知识检索与答题规则

### Modified Capabilities

- （无主库基线）

## Impact

- **代码**：`match_event_by_vector`（或前置门禁）、`intent_classification` 提示、`intent_graph` / intent stream 路由、`call_clinic_agent`、`clinic_graph`（条件边或等价）、`clinic_answer`、`data_requirement` 提示；可能 `clinic.py`/`tip` 步进表读同一 flag
- **行为**：history 问法进 clinic 人格答题；suggest/conversation 仍可检知识；纯 history 不写 knowledge_ids

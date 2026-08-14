## Why

分类前备注探针把 filter 结果压成一行中文摘要塞进提示，却不在 Python 侧写入 `event_id`，映射能否成立全靠模型读懂旁白；同时本地 OOV 抽词脆弱。真正要解决的是：用户说「AD」时，用本设备历史备注反查对应字典事件。应改为先让 LLM 翻译原话里的动作与事件名，再用规则对字典外名称调 Go filter 定事件。

## What Changes

- **BREAKING（行为）**：删除分类前备注探针路径（`extract_oov_token` 门控、分类前提示注入 `remark_probe_hint`）。进行中计时探针保留并仍在分类前注入。
- 分类后：字典匹配失败的名称作为 `remark` 调现有 Go `filter`（本设备、近窗、小 limit、空 `eventIds`）；按 `event_id` 聚合命中。
  - **唯一命中**：写入字典 `event_id` / `event_name`，`remark_keyword` 为该专名，再走既有确认。
  - **多命中**：消歧（让用户选叶子），不得静默取众数。
  - **零命中**：反馈无法识别对应的事件；禁止 `is_new_event` 建档；**首次记 AD（历史备注从未出现）亦无法识别**，不得用常识猜「营养品」再确认落库。
- 分类提示调整：允许将表内活动的简称/进行状态对到真名（如「正在爬」→「爬练习」）；禁止把表外专名凭常识升格成类别事件（AD ≠ 营养品）。仍不得用用户口头关键字绑定 `op`。
- 字典匹配规则加强：在精确/包含之外，可剥常见进行态前缀（如「正在」「在」）再做包含匹配，避免「正在爬」误入备注反查。
- 本版不做「原话与表内名无共字则强制备注校验」可选层。

## Capabilities

### New Capabilities

- （无）

### Modified Capabilities

- `history-remark-filter`：字典外定事件从「分类前探针 + 摘要注入」改为「分类后备注反查」；零命中改为无法识别（取消常识猜事件）。
- `langgraph-intent-graph`：图结构去掉分类前备注探针；分类后增加备注反查（或等价节点）；进行中探针保留；分类提示增加简称/状态 vs 专名升格两条原则。

## Impact

- **Python**：`remark_probe.py`（拆分或收窄为仅进行中）、`intent_graph.py`、`intent_classification.py`、`classify_intent.py`、`intent_state.py`；可能复用 `clarification.py` 多选项消歧；`thinking_messages` / 流式文案。
- **HTTP**：仍用现有 `get_filtered_history_events(..., remark=)`；不改 Go filter 契约。
- **规格**：覆盖未收版 change 中已有的 `history-remark-filter` / `langgraph-intent-graph` 行为；对照基线 `v0.0.1` 无同名 capability 时以本 delta 与既有 change 链为准。
- **不改**：兄弟仓 DDL、意图缓存写入形状（仍可含 `remark_keyword`）、禁止新建事件类型。

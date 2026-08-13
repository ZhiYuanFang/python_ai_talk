## Why

「现在不爬了，改坐了」这类复合句需要结束最近一次计时事件并开始另一件。Go 已按 `eventId + action=end` 补最近一条结束时间，但 Python 分类常把两件都当成记录、确认话术也不点动作；ASR 同音（怕/爬、做/坐、该/改）更容易拆错。同时 create 默认 `endTime=0`，一次性/计数会被当成进行中计时。分类前注入进行中摘要只会无限打补丁，不纳入本变更。

## What Changes

- 分类提示要求复合句按子句拆到 `events[]`，**每件自带 action**（`end` 与 `start`/`one` 不得揉成一条）；不注入进行中历史。
- 分类提示增加同音不同字提醒（怕≈爬、做≈坐、该≈改），对上字典真名再填 id；对不上则 `missing` 或闲聊。偶发认错可接受。
- 结束计时：Python 只交正确叶子 `eventId` 与 `action=end`；MUST NOT 查进行中、MUST NOT 填 `history_id`。Go 负责补最近一条结束时间。
- 多事件确认话术 MUST 带每件动作（结束「爬练习」并开始「坐练习」），禁止只列名称说「记录」。
- 落库前按字典 `event_type` 覆盖时间：非 `time` 一律 `endTime = startTime`；`time` + start 才允许 `endTime=0`。事件类型 MUST NOT 由 LLM 返回。
- batch 中 `end` 项排在 `create` 之前。

## Capabilities

### New Capabilities

- （无。行为落在既有能力的增量上。）

### Modified Capabilities

- `langgraph-intent-graph`: 分类提示教复合拆动作与同音；叶子表可带字典 type 供选 action；禁止注入进行中摘要；禁止采信 LLM 的 `event_type`
- `intent-python-history-crud`: 结束只交 `eventId + action=end`；非计时 `endTime=startTime`；batch 先 end 后 create
- `feeding-intent-user-confirmation`: 多事件确认 MUST 点出每件名称与动作
- `intent-analysis`: 复合切换句 MUST 拆成多子项且各带 action

## Impact

- **Python**：`intent_classification.py` 提示词、`classify_intent.py`（忽略 LLM 类型）、`history_crud.collect_event_items`（字典盖时间、end 不填 history_id、排序）、`intent_pipeline.py` / `clarification.py` 确认话术
- **API**：`IntentResponse` 字段不变；`events[].action` 与 `confirm_message` 文案变化
- **Go / 前端**：不改契约；结束仍走既有 batch `op=end` / end-latest
- **非目标**：不注入进行中探针；不改查记录模板；不改 clinic/tip；不生成测试文件

## Why

分类提示用「上一次 / 什么时候 / 不 X 了」等话术把用户原句映射到 `op`，本地再用 `looks_like_history_query` 猜是不是查询。结果「删除上一次坐练习」稳定被当成查记录，同音句（怕/爬）也只能继续加规则。话术一变就要改提示，形成套娃。

## What Changes

- 分类提示只描述返回字段含义与事件表约束，MUST NOT 用用户关键字或句式模板判断 `op`（含「上一次」= read）。
- 删除 `looks_like_history_query`（及可空的 `query_utterance.py`）。是否查询由 LLM 按字段含义判断；备注探针改为抽出字典外词才打 HTTP，不再先判查询句。
- 缓存 miss 后、分类前注入本设备**进行中计时**摘要（事件名 + 字典 id + 开始时间；无则明确没有）。MUST NOT 注入 `history_id`。结束仍只交 `eventId + action=end`，由 Go 补最近一条。
- 查记录确认话术仅当 `op=read` 时使用；MUST NOT 因 `action=search` 把删除/结束说成「是否查询历史」。
- 意图缓存不再用本地查询正则丢掉 create 命中。

## Capabilities

### New Capabilities

- （无。行为落在既有能力的增量上。）

### Modified Capabilities

- `langgraph-intent-graph`: 提示改为字段定义；允许并要求注入进行中计时摘要；去掉话术关键字与同音对照表
- `history-remark-filter`: 备注探针不再依赖查询句正则，仅在字典外词时触发
- `feeding-intent-user-confirmation`: 查记录确认只认 `op=read`
- `intent-cache-flywheel`: 不得用本地查询句检测拦截缓存
- `intent-analysis`: 删除上一次记录 MUST 能分类为 `delete` 而非 `read`（不靠关键字表）

## Impact

- **Python**：`intent_classification.py`、`remark_probe.py`（或同节点加进行中）、`classify_intent.py`、`match_intent_cache.py`、`clarification.py`；删除 `query_utterance.py`
- **API**：字段不变；`confirm_message` / 分类 `op` 更准
- **Go**：filter 契约不变；end-latest 不变
- **非目标**：不改落库时间盖写与 batch 排序；不改 clinic/tip；不生成测试文件

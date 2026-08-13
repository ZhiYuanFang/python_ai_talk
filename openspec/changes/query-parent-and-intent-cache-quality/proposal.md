## Why

查记录确认话术常写成「该事件」，用户不知道系统听成了什么。分类提示只给叶子，用户问「上一次换尿布」时无法命中父事件，更不会展开尿尿/拉屎取最近一条。点查模板不论 one/time/number，计时进行中也说不清。意图缓存只有相似度门槛、命中即免确认执行，错误条目会越积越稳；已退役的 `REBUILD_FEEDING_STANDARD_EVENTS` 仍留在生产环境文件里。

## What Changes

- 查记录确认话术由 Python 拼出，MUST 带字典事件名（叶子或父），禁止「该事件」兜底。
- 分类提示注入全量树并标明父/叶子：`read` 命中父只输出父 id；`create/update/delete` 禁止用父 id。
- 查父与查叶子一样首轮确认（是/否，不是选叶子）；确认后递归展开子孙叶子拉史，按 `startTime` 取最近一条，播报点出父名与叶子名。记事件命中父仍消歧。
- 点查模板按 `event_type` 区分一次性 / 计时（含进行中）/ 计数；相对时间与日汇总不改。
- 意图缓存增加质量分：检索须相似度与质量分双门槛；同一设备短窗内对刚免确认执行过的同一问再问，对该条扣分并当未命中；定时清理低分条目。缓存查父载荷存父 id，不存展开后的叶子列表。
- 新增启动一次性清空 `feeding_intents` 的环境变量（默认关）。删除已退役的 `REBUILD_FEEDING_STANDARD_EVENTS`。

## Capabilities

### New Capabilities

- （无。行为落在既有能力的增量上。）

### Modified Capabilities

- `parent-event-disambiguation`: 消歧仅约束 create/update/delete；`op=read` 命中父走是/否确认，确认后展开叶子拉史，MUST NOT 改成选叶子
- `intent-history-query`: 点查按事件类型模板播报；父展开后塌成最近一条并点名；确认句带事件名
- `intent-cache-flywheel`: 质量分、双门槛、短窗重复扣分、定时清理；查父缓存存父 id
- `langgraph-intent-graph`: 分类提示注入全量树（父/叶）；read 父输出父 id，执行层展开
- `feeding-intent-user-confirmation`: 查记录确认 MUST 点出事件名
- `env-config`: 新增 `CLEAR_FEEDING_INTENTS_ON_STARTUP`；文档与环境文件删除 `REBUILD_FEEDING_STANDARD_EVENTS`
- `feeding-events-vector-store`: 不得再实现或配置标准事件向量重建开关
- `event-vector-dict-fields`: 移除 `ENV-gated one-shot standard rebuild`

## Impact

- **Python**：分类提示、`classify_intent`、`try_handle_pending`（read 父不得消歧）、`speak_history` 展开与模板、`intent_cache_store` 质量分与清理、启动预热、`settings.py`
- **配置**：`.env.example`、`env/.env.prod`、`docker-compose.yml`、`docs/deploy-guide.md`
- **API**：`IntentResponse` 字段不变；`confirm_message` / `content` 文案变化
- **Go / 前端**：不改契约；语音仍播 `confirm_message` 与 `content`
- **非目标**：不改 clinic/tip/care-alert 主路径；不改日汇总压缩；不生成测试文件

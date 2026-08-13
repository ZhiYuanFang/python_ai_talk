## Why

喂养意图把「这句话像哪个事件名」当成飞轮单位：向量只取 Top-1、用户表达整句绑到单个 `event_id`，高置信短路 LLM，一句话里的多事件会被漏记；查/改/删没有一等操作。Go 在 Python 返回后仍用原文二次匹配、自己挂 `pendingChild`、自己 `AddHistory` 并拼话术。非流式 `/v1/analyze/intent` 又被改成 clinic 陪伴（`intent-sync-as-clinic`），与流式意图图语义分裂。

查记录还会把「今天/最近七天」等枚举在 Python 里算错窗，且常在未定事件时拉全类型原始行，prompt 过长。现实还有「上一次什么时候吃的 AD」：AD 不是字典事件，而是营养品记录的备注。现网 filter 不能按备注搜，分类还会把字典外词当成 `is_new_event`。

需要把 intent 收成 **Python 独自完成的多事件 CRUD 智能体**（意图缓存加速、批量落库、模板回执、备注探针定事件），Go 只透传结果并提供 **一条批量写接口 + filter 备注模糊**；陪伴与意图 URL 拆开。

## What Changes

- **BREAKING**：删除单事件数据飞轮相关代码（`add_user_expression`、用户表达的 `increment_match_count` / `increment_success_count` / `check_and_cleanup`）。改为 **意图缓存飞轮**：独立问答句 → 整份 `{op, events[]}`（可含 `remark_keyword`）；仅确认且至少一条落库成功后写入。改/删缓存不得固化 `history_id`。
- **BREAKING**：Python 确认后经 **一条** Go 批量 history HTTP 执行增/改/删/结束；查在意图图内按事件（及可选备注）拉史，用 **模板** 填 `content`。Go 语音 **SHALL NOT** 再按 `target_type`/`action` 写库、对原文二次匹配、缺数量追问或维护 `pendingChild`。
- **BREAKING**：意图图 **SHALL NOT** 再调用 `call_clinic_agent`，**SHALL NOT** 再走 `judge_data_requirement` + 历史答题 LLM。`feeding` 不得导入 `clinic`。
- **BREAKING（作废 `intent-sync-as-clinic`）**：非流式 `POST /v1/analyze/intent` 与 `/intent/stream` **同一套**意图图。
- 新增 `POST /v1/clinic`（非流式），与 `/clinic/stream` 共用 `clinic_graph`；响应为 `{answer, answer_id}`。
- Go：成长建议与前端陪伴改打 clinic 非流式；`chatWithResult` / 历史问答仍打 `/intent`，只播 `content` 并回传 `conversation_id`。
- **禁止新建事件类型**：字典外专名不得 `is_new_event` 建档；记事件时进 `missing_events` 并说明；查记录时当备注候选，先探针再确认。
- 分类 miss 后默认 **先确认再落库**（高置信单次 create 除外）。多事件一律软确认。
- 落库回执必须让用户感知：全成功 / 部分成功须同时说明成功项与失败原因。
- 查记录必须先定事件（或日汇总压缩）；点查每条带备注。Go filter 新增 `remark` 模糊；`history.remark` 保持可空，并提供可复制 DDL 加索引。
- 时间窗由分类直接给 Unix 秒（注入「现在」上海时区）；删除 `today|yesterday|last_7_days` 映射。clinic/tip/care-alert 拉史对齐同一套 unix + 事件约束。
- 会话连续性：`conversation_id` + 内存 `clarification_store` pending。无 cid 或无 pending = 首轮。clinic `companion_session` 不用于意图 CRUD。

## Capabilities

### New Capabilities

- `intent-cache-flywheel`：已确认且落库成功的独立问答句缓存为整份 CRUD 意图（含 multi / `remark_keyword`）；改/删不缓存记录主键
- `intent-python-history-crud`：Python 经批量 history HTTP 执行 CRUD，模板回执（含部分成功）
- `clinic-sync-http`：非流式 `POST /v1/clinic`，与 stream 同图、陪伴响应外壳
- `intent-history-query`：点查 / 日汇总、Unix 窗、先定事件、模板播报、备注进史
- `history-remark-filter`：Go filter 备注模糊、可空备注、可复制索引 SQL、AD 类探针与确认
- `intent-session-continuity`：`conversation_id` + pending 判断首轮 vs 连续对话

### Modified Capabilities

- `intent-analysis`：非流式 `/intent` 恢复为意图图；禁止新建事件类型
- `intent-stream-response`：stream 最终 answer 与非流式 `IntentResponse` 字段语义一致
- `feeding-intent-data-flywheel`：删除单事件用户表达飞轮代码与检索路径
- `feeding-intent-vector-matching`：不得以单事件高置信吞掉多事件/非 create；意图缓存优先
- `langgraph-intent-graph`：缓存 →（可选备注探针）→ 分类 → 确认 | 批量执行 | 模板查记录；移除 clinic / 历史答题 LLM
- `intent-target-type-routing`：history 留在意图图；conversation 短回复 END
- `intent-companion-bridge`：意图路径不再读写作伴会话、不再调用 clinic agent
- `nl-history-via-clinic`：查记录改由意图图拉史模板答题
- `clinic-stream`：补充非流式同源入口
- `dead-suggest-path-removal` / `growth-suggestion`：成长建议改走 clinic HTTP

## Impact

- **Python**：意图图、分类提示、飞轮删除、意图缓存、批量写客户端、filter 备注、模板回执、`/intent` 同图、`POST /v1/clinic`、clinic/tip 拉史 unix 对齐
- **API**：`/intent` 恢复喂养 CRUD；新增 `/v1/clinic`；`IntentResponse` 增加 `op` / `remark_keyword` / `missing_events`（兼容期保留 `action`）
- **Go（`go_ai_talk`）**：语音透传；新增 `POST /device/history/api/event/batch`；filter 增加 `remark`；`docs/migrations` 可复制 SQL；成长建议改 clinic
- **数据库**：`history.remark` 保持可空；加复合索引 + 备注检索索引（见 SQL 文件，需人工执行）
- **前端**：陪伴从 `/intent` 迁到 `/v1/clinic`（本仓不实现 Flutter）
- **非目标**：不改 clinic/tip 流式主路径（除同步 clinic 与拉史对齐）；不改 care-alert / Q&A 知识飞轮主逻辑（仅拉史参数对齐）；不生成测试文件

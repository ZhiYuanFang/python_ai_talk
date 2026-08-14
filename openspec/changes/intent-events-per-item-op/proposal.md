## Why

顶层 `op`/`action` 与 `events[]` 双轨并存：复合句（结束睡眠 + 开始爬练习）常被整单标成 `op=update`，落库把「开始」当成改已有记录并失败。CRUD/读语义本应按**事件项**表达；顶层 `action=multi` 在「一律数组」后亦多余。Go 语音主路径不消费顶层 `op`，可安全删除并对齐兄弟仓。

## What Changes

- **BREAKING**：`IntentResponse` / 图内 `IntentResult` **删除顶层 `op` 与顶层 `action`**。
- **BREAKING**：涉事件意图（喂养 CUD、查记录）MUST 以非空 `events[]` 为唯一事件载体；每项 MUST 自带 `op`（`create|update|delete|end|read`），可选 `action`（`start|one|end`，服务 create/end 形态）、`event_id`/`event_name`/`quantity`；查记录项 MUST 可带自有 `start_time`/`end_time`（及可选 `remark_keyword`）。
- 单事件与多事件统一：`len(events)>=1` 即多事件管线的特例；不再用顶层字段平行表达单叶子。
- 闲聊 / 退出：`target_type=conversation|exit`，**不要求** `events`（可空）。
- 落库：仅按子项 `op` 组装 batch；`end` 在前；仅 `update|delete` 现查 latest；**禁止**用已删除的顶层 op 广播。
- 图路由：由 `events[].op` 集合与 `target_type` 决定 batch / speak_history / END。
- 分类提示与确认话术按子项 `op`/`action` 表达；结束计时 MUST 为子项 `op=end`，MUST NOT 等同于 `update`。
- Go（`go_ai_talk`）同步：客户端去掉顶层 `Op`/`Action`（或 Action 仅兼容期忽略）；`IntentEvent` 增加 `op` 与读窗字段；透传逻辑仍播 `content`/`confirm_message`。

## Capabilities

### New Capabilities

- `intent-events-envelope`：意图信封与 `events[]` 子项契约（无顶层 op/action；读/写均在子项；闲聊退出无事件）。

### Modified Capabilities

- `intent-analysis`：分类产出改为 events 子项 op；删除对顶层 op/action 的依赖描述。
- `langgraph-intent-graph`：路由与确认后执行、落库/查记录按子项 op / target_type；缓存载荷以 events 为主。
- `intent-target-type-routing`：history/feeding/conversation/exit 与 events 关系。
- `feeding-intent-user-confirmation`：确认话术按子项动作；确认后续聊保留 events。

## Impact

- Python：`intent` schema、`IntentResult`、`classify_intent` 提示与后处理、`history_crud`/`execute_history_crud`、`intent_graph` 路由、`speak_history`、`intent_pipeline`/pending、意图缓存读写。
- Go：`AnalyzeIntentResponse`、`IntentEvent`、`mapPythonRespToIntent` / 日志；batch API 子项 op 不变。
- 对外 HTTP 意图 JSON：**BREAKING**（调用方勿再读顶层 `op`/`action`）。
- 不引入测试文件；业务注释中文。

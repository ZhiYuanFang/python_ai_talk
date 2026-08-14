## 1. Schema 与提示

- [x] 1.1 `IntentEvent` / `IntentEventItem`：增加 `op`、读窗 `start_time`/`end_time`、可选 `remark_keyword`；明确子项可选 `action`
- [x] 1.2 `IntentResponse` / `IntentResult`：删除顶层 `op` 与顶层 `action`；响应组装不再填充二者
- [x] 1.3 重写分类提示：无顶层 op/action；涉事件只填 `events[]` 且每项有 `op`；结束= `op=end`；闲聊/退出无 events

## 2. 分类与归一

- [x] 2.1 `classify_intent`：校验 feeding/history 须非空 events；缺子项 op 时用 action+字典 type 推导；去掉对顶层 op/action 的默认与 multi 补丁逻辑
- [x] 2.2 提供「仅有旧顶层字段」时投影为 `events[0]` 的兼容辅助（缓存/过渡），主路径只读数组

## 3. 落库与查记录

- [x] 3.1 `collect_event_items` / `infer_op`：以子项 `op` 为准组装 batch；删除顶层 op 广播；仅 update/delete 现查 latest
- [x] 3.2 `execute_history_crud`：按子项集合判断是否执行；回执与缓存写入带 events[].op
- [x] 3.3 `speak_history`：按 `op=read` 子项各自时间窗（及 remark）拉史并模板播报；弱化顶层 event_ids/单窗主路径

## 4. 图路由与确认管线

- [x] 4.1 `intent_graph` 路由：按子项 op 集合与 target_type 分支；不再 `infer_op` 读顶层
- [x] 4.2 `intent_pipeline` / pending / 确认话术：挂载完整 events；确认后原样执行；话术按子项 op
- [x] 4.3 意图缓存读写：载荷以 events（含 op）为准；旧载荷无 events 则投影或跳过

## 5. Go 同步（go_ai_talk）

- [x] 5.1 `AnalyzeIntentResponse` 删除顶层 `Op`；删除或停用顶层 `Action` 依赖；日志不再打印顶层 op/action 作为权威
- [x] 5.2 `IntentEvent` 增加 `op`、`start_time`、`end_time`、`remark_keyword`；`mapPythonRespToIntent` 透传 events
- [x] 5.3 确认 `applyUnifiedIntentResult` 仍只播 confirm/content/exit，不解析子项落库

## 6. 验收

- [x] 6.1 手工：结束睡眠+开始爬练习 → 确认 → 睡眠 end 成功且爬练习 create 成功
- [x] 6.2 手工：单事件开始 / 仅结束 / 查记录（子项自带窗）/ 闲聊无 events
- [x] 6.3 `openspec validate intent-events-per-item-op --strict`

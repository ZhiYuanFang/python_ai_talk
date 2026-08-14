## Context

复合 CUD 依赖顶层 `op` 广播到所有子项，导致 `end+start` 中 start 被当成 update。探索结论：意图侧与 Go batch 对齐为「每项自有 op」；顶层 `op` 与顶层 `action`（含 `multi`）删除。Go `AnalyzeIntentResponse` 有顶层 `Op` 但仅日志；`deepSeekUnifiedIntent` 不承载 `Op`；`applyUnifiedIntentResult` 透传 confirm/content/exit，不读顶层 op。读记录改为 `events[].op=read` 且每项自带时间窗。闲聊/退出无 events。

## Goals / Non-Goals

**Goals:**

- 删除顶层 `op`、`action`；涉事件一律非空 `events[]`，每项有 `op`。
- 统一单/多事件落库与查记录管线；复合句按子项正确 create/end/update/delete/read。
- 提示：结束计时 = 子项 `op=end`，不再绑在 update。
- Go 客户端结构同步删顶层 Op（及顶层 Action 字段或停止依赖）；子项扩展 op/时间窗。

**Non-Goals:**

- 不改 Go history batch HTTP 契约（本就 items[].op）。
- 不恢复 Go 侧按 action 写库。
- 不强制 Flutter 本变更内改版（若只消费 content/confirm 可暂不动）。
- 不写测试文件。

## Decisions

1. **信封 vs 数组**  
   信封：`target_type`、`content`、`need_confirm`、`confirm_message`、`conversation_id`、匹配元数据等。  
   数组：仅 feeding CUD 与 history 读。  
   conversation/exit：`events` 空。

2. **子项 op 词汇**  
   `create | update | delete | end | read`。  
   子项 `action` 保留为可选：`start | one | end`（create/end 形态）；update/delete/read 可空。  
   **相对**：只留 action —— 无法表达 update/delete。

3. **删除顶层 action**  
   不再用 `multi`/`reply`/`exit`/`search` 作顶层动作；exit/闲聊看 `target_type`；多事件看 `len(events)`。  
   兼容：若旧缓存仍带顶层 action，读入后忽略或投影进 events（迁移期）。

4. **路由**  
   - 任一项 `op in {create,update,delete,end}` 且已确认 → `execute_history_crud`  
   - 任一项 `op=read` 或 `target_type=history` → `speak_history`（按项拉史）  
   - `conversation`/`exit` → END（播 content）  
   - `need_confirm` → END（不执行）

5. **落库**  
   `collect_event_items` 以子项 `op` 为准；缺省时可由 `action`+字典 type 推导（兜底）；**禁止**已删除顶层字段参与。  
   仅 `update|delete` 调 `_fill_latest_ids`。

6. **读窗**  
   每项 `start_time`/`end_time`（Unix 秒）；可选 `remark_keyword`。废弃对「整单唯一时间窗 + 顶层 event_ids」的主路径依赖（兼容期可从 events 投影）。

7. **Go**  
   删 `AnalyzeIntentResponse.Op`；`IntentEvent` 加 `op`、`start_time`、`end_time`、`remark_keyword`；顶层 `Action` 删除或标废弃且映射层不依赖。透传逻辑不变。

## Risks / Trade-offs

- [LLM 漏填 events 或子项 op] → classify 后校验：feeding/history 无有效 events 则软失败或追问；子项缺 op 时用 action+type 推导。  
- [意图缓存旧 payload 含顶层 op/action] → 命中后投影为 events；无法投影则视为未命中。  
- [调用方仍读顶层 action] → BREAKING 文档与 Go 同步；语音主路径只播 content。  
- [父事件消歧 pending] → pending 仍挂完整 `events` 列表，确认后原样执行。

## Migration Plan

1. Python：schema → 提示 → collect/路由/speak/cache → pipeline。  
2. Go：客户端结构与日志。  
3. 同发或先 Python 仍短暂 omit 兼容，再删字段。  
4. 回滚：恢复顶层字段并恢复 `infer_op` 广播（不推荐长期）。

## Open Questions

- 无。顶层 `action` 按用户要求删除；读进 events 每项自带窗。

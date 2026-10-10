## 1. Schema 与提示词

- [x] 1.1 `IntentEventItem` / `IntentResult` / `IntentResponse`：删除 `remark_keyword`，统一为 `remark`（顶层与子项）
- [x] 1.2 `IntentState` 与相关常量列表：`remark_keyword` → `remark`
- [x] 1.3 `FEEDING` 分类 `prompts/system.py`：字段说明与 JSON 模板仅保留 `remark`；中文说明覆盖查史专名与 create 明细

## 2. 澄清、管道与图节点

- [x] 2.1 `clarification.py`：PendingClarification、建 pending、查史确认话术、`pending_to_response_fields`、`leaf_intent_result` 等全部改 `remark`
- [x] 2.2 `intent_pipeline.py`：确认后执行、history confirm、postprocess 传参全部改 `remark`
- [x] 2.3 `resolve_remark_event.py`：反查写回与状态字段改 `remark`
- [x] 2.4 `classify_intent.py`、`speak_history.py`：读写与 filter 专名来源改 `remark`
- [x] 2.5 `intent_events.py` 归一化：传播/回填使用 `remark`

## 3. 落库与飞轮

- [x] 3.1 `history_crud.collect_event_items`：batch `remark` 取自 `events[].remark` / 顶层 `remark`（不读旧键）
- [x] 3.2 `rewrite_standalone_document`、`execute_history_crud` 飞轮 payload：键改为 `remark`
- [x] 3.3 `intent_cache_store` 模块注释与载荷约定改为 `remark`
- [x] 3.4 （建议）`format_confirm_slot`：create 且 `remark` 非空时附带「（备注…）」

## 4. Shared 与清零校验

- [x] 4.1 `app/shared` 中 `data_requirement` / `fetch_history` 等凡含 `remark_keyword` 处改为 `remark`
- [x] 4.2 全仓搜索：除迁移实现外，运行时与 feeding 提示词无 `remark_keyword` 字段名
- [x] 4.3 `openspec validate unify-intent-remark-field --strict` 并修规格问题

## 5. Chroma 启动迁移（仅 feeding_intents）

- [x] 5.1 `settings` + `.env.example`：新增 `migrate_intent_remark_keyword_on_startup`（默认 false）
- [x] 5.2 `intent_cache_store`：实现迁移（顶层/`events[]` 旧键→空 `remark`，删旧键；返回计数）
- [x] 5.3 `main` 预热后：若 clear 开则跳过迁移；否则按迁移开关执行并打告警日志
- [x] 5.4 `openspec validate unify-intent-remark-field --strict`
- [x] 5.5 `docker-compose.yml`：注入 `MIGRATE_INTENT_REMARK_KEYWORD_ON_STARTUP`（与 CLEAR 同级）
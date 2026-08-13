## 1. Go：备注索引 SQL 与 filter

- [x] 1.1 在 `go_ai_talk/docs/migrations/history_remark_filter_index.sql` 提供可复制 DDL：复合索引 + 可选 ngram FULLTEXT；**不**把 `remark` 改为 NOT NULL（中文注释说明 LIKE '%x%' 与可空语义）
- [x] 1.2 `DeviceHistoryFilterReq` 增加 `remark`；`ListDeviceHistoryFilter` / remote adapter / 契约同步；空备注行不参与模糊匹配；无 eventIds 时 limit≤20
- [x] 1.3 Python `http_client.get_filtered_history_events` 透传 `remark`

## 2. Go：批量写与语音透传

- [x] 2.1 新增 `POST /device/history/api/event/batch`：`items[]` 支持 create/update/delete/end，部分成功返回每项结果与原因（中文注释）
- [x] 2.2 `AnalyzeIntentResponse` 增加 `op` / `remark_keyword` / `missing_events`；`AnalyzeIntent()` 仍打 `/v1/analyze/intent`
- [x] 2.3 `applyUnifiedIntentResult` 收成透传：need_confirm 播确认句；否则播 content；exit 结束会话
- [x] 2.4 删除或停用 land plan 写库、`handleMultiEventIntent`、`pendingChild`、preamble 短路
- [x] 2.5 新增 Clinic 非流式客户端打 `POST /v1/clinic`；`callDeepSeekGrowthSuggestion` 改用该接口
- [x] 2.6 `chatWithResult` 继续 `AnalyzeIntent`；禁止意图失败回退成 clinic 语义

## 3. Python：拆除单事件飞轮

- [x] 3.1 删除 `add_user_expression`、用户表达计数/清理及 `apply_flywheel_after_leaf_resolution` 飞轮写入
- [x] 3.2 检索排除或清理 `feeding_events` 中 `source=user`；标准事件向量同步保持可用
- [x] 3.3 知识库 `source=user` 不得误删

## 4. Python：意图缓存与 HTTP

- [x] 4.1 `http_client` 增加 batch 封装（GoFrame data 解包，中文注释）
- [x] 4.2 扩展 `IntentResponse`：`op`、`remark_keyword`、`missing_events`；子项可选 `history_id`；保留 `action`
- [x] 4.3 新增意图缓存存储（独立 Collection，document=改写独立句，metadata=op+events+可选 remark_keyword）
- [x] 4.4 确认且至少一条落库成功后写缓存；改/删不得固化 `history_id`；「嗯/是的」不得当 document
- [x] 4.5 `match_intent_cache`：高置信采用缓存；改/删命中后现查再执行

## 5. Python：分类、探针、确认、模板

- [x] 5.1 重写 `intent_graph`：缓存 → 可选备注探针 → 分类 → 确认 END / batch / 模板查记录；删除 `call_clinic_agent` 与 feeding 对 clinic 的导入
- [x] 5.2 分类提示：增删改查、只匹配已有叶子、字典外当备注、禁止 `is_new_event`、查记录输出 unix + event_ids + remark_keyword；去掉 suggest
- [x] 5.3 点查句式 + 字典外词：先 filter 备注探针，只注入一行事件聚合摘要
- [x] 5.4 分类默认 need_confirm；多事件软确认；高置信单一 create 可免确认；硬匹配「是的/1/取消」不走澄清 LLM
- [x] 5.5 `match_event_by_vector`：查询句与复合句不得单事件高置信 END
- [x] 5.6 `execute_history_crud`：一次 batch；模板 `content` 覆盖全成功/部分成功/全失败
- [x] 5.7 查记录：删除枚举时间映射；用 unix + event_ids + 可选 remark；点查模板带备注；日汇总先压缩；删除意图侧 `judge_data_requirement` 与历史答题 LLM
- [x] 5.8 多事件确认 pending 保存完整 `events[]`；确认话术列出全部名称
- [x] 5.9 clinic/tip/care-alert 拉史改为传入已计算 unix，不得再传 today/last_7_days 等枚举

## 6. 路由：intent 同图 + clinic 非流式

- [x] 6.1 `analyze_intent` 改回与 stream 相同 pending / 图 / 后处理；作废 clinic 伪装
- [x] 6.2 删除或移出 `call_clinic_agent.py`，确保无 feeding 引用
- [x] 6.3 `POST /v1/clinic`：ClinicRequest、clinic_graph、返回 answer/answer_id
- [x] 6.4 更新 `thinking_messages`：去掉 call_clinic_agent，补上缓存/探针/落库/查记录
- [x] 6.5 所有新增/改动业务代码补全中文注释

## 7. 校验

- [x] 7.1 运行 `openspec validate rebuild-intent-crud-agent --strict` 并修复规格问题
- [x] 7.2 对照规格手工核对：非流式 /intent 记事件、复合句不丢件、部分入库回执、AD 备注确认、/v1/clinic 陪伴、Go 不再二次匹配

## 8. Python：拆除 feeding_events 与事件名匹配（方案 B）

- [x] 8.1 重写 `intent_graph`：`remark_probe` 直连 `classify_intent`；删除 `match_event_by_vector` 节点与路由
- [x] 8.2 删除 `app/feeding/graphs/nodes/match_event_by_vector.py`；`thinking_messages` / `stream_intent_response` 去掉该节点文案
- [x] 8.3 删除 `app/feeding/services/event_vector_store.py`；清除 `event_cache` / `main.py` / `scripts/build_vector_db.py` 对 `feeding_events` 的初始化与同步
- [x] 8.4 分类默认 `need_confirm`；免确认仅意图缓存高置信命中；去掉事件名向量高分免确认
- [x] 8.5 知识库 `mother_baby_knowledge` 与 `feeding_intents` 不得误删；启动不得再创建 `feeding_events`
- [x] 8.6 运行 `openspec validate rebuild-intent-crud-agent --strict`；手工确认首次记事件走分类、复合句不短路、查询句不落 create

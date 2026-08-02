## 1. Intent：门禁与路由

- [x] 1.1 增加查询句检测（何时/上次/分别/多少等）；`match_event_by_vector` 命中则强制降级 LLM，不提交 feeding
- [x] 1.2 强化 `intent_classification` 提示：查上次/何时/分别 → history，禁止 feeding
- [x] 1.3 `route_after_classify` 与 intent stream：`history` → `call_clinic_agent`（摘掉 history→generate_response 边）

## 2. Clinic agent：跳过知识检索

- [x] 2.1 `call_clinic_agent` 在 `target_type=history` 时写入 `skip_knowledge=True`
- [x] 2.2 `clinic_graph`：`fetch_history` 后按 `skip_knowledge` 条件边跳过 `search_vectors`；同步 clinic HTTP 线性步进表（若存在）

## 3. 答题与上下文

- [x] 3.1 抽取历史字段裁剪（eventName/eventNumber/startTime/endTime/remark），供 clinic_answer 等使用
- [x] 3.2 更新 `clinic_answer`：查记录题按记录答时间、支持「分别」、放宽约 50 字限制
- [x] 3.3 更新 `data_requirement` 提示：上一次 / 多事件分别 的 event_ids 与 time_range/limit 指引

## 4. 校验

- [x] 4.1 核对：「上一次拉屎是什么时候」非 feeding 且有时间答；「睡觉拉屎分别」两时间；「拉屎了」仍可 feeding；history 无 knowledge 检索日志

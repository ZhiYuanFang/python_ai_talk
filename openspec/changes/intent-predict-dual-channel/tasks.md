## 1. 模型与飞轮

- [x] 1.1 `TargetType` / schema / `SegmentDraft` 增加 `predict`；字段 `predict_channel`、`time_answer`（分维；非 predict 清空）
- [x] 1.2 `type_cue_store`：allowed 含 predict；payload 校验两维；admin bulk 兼容
- [x] 1.3 TYPE LLM 提示与解析：输出两维；纠偏「还有多久醒来/睡觉」→ predict，勿一律 history；中文注释

## 2. Go 契约与 HTTP（孪生 + 本仓）

- [x] 2.1 孪生 Go：`GET /voice/internal/api/predict/imminent/pending?deviceNo=`（密钥中间件；`events`；空键 []）— Go 已落地，本仓跳过实现
- [x] 2.2 `http_client`：imminent pending GET；复用 active-eta GET 与内部密钥；解包 `data.events` / `data.items`

## 3. 播报与路由

- [x] 3.1 实现 `speak_predict`：按 channel 匹配锚点；clock / remain 文案；remain 超时「已经过了预计时间」
- [x] 3.2 intent 图：`target_type=predict` → `speak_predict`；无数据估不准且不回落「上一次…用时」
- [x] 3.3 组装/确认/飞轮写入带回 `predict_channel`、`time_answer`；predict 优先于 history_mode「多久」门闩

## 4. 验收

- [ ] 4.1 手工：「大概还有多久醒来」+ 进行中睡眠 ETA → remain 剩余或「已经过了预计时间」
- [ ] 4.2 手工：「还有多久睡觉」+ imminent 有睡眠 nextAt → remain/clock 符合 time_answer
- [ ] 4.3 手工：无 Redis / 未配密钥 → 估不准，不出现「上一次…用时」

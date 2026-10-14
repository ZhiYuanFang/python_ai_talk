## 1. 孪生与目录

- [x] 1.1 孪生 Go：device internal GET 对齐 App `appointment/next`（deviceNo+eventId→nextAt；密钥中间件；无行 0）
- [x] 1.2 Python：事件目录可读 `isAppointment`（options）；按**命中事件自身**字段判定（对齐 Go `event.is_appointment`，不按根/子树聚合）
- [x] 1.3 `http_client`：预约 next internal GET；中文注释

## 2. 本地预测工具

- [x] 2.1 按 Flutter `event_next_predictor` 场景封装：近 7 日窗、加权中位间隔、nextAt、expect 用量/时长；中文注释
- [x] 2.2 命中事件 `isAppointment` 旁路间隔，用该 eventId 调 appointment nextAt；无约定明确降级
- [x] 2.3 样本不足返回可区分结果（供上层直接「数据量太少，无法预测」）

## 3. Redis 算法快照

- [x] 3.1 设备级快照读写（独立 key 前缀，TTL 600s）；复用 `create_async_redis_client`
- [x] 3.2 意图 C/U/D（及改史 end）落库成功后 DEL 该 device 快照
- [x] 3.3 快照命中跳过 7 日重拉与重算，不写入分类飞轮

## 4. speak_predict 兜底编排

- [x] 4.1 Go 命中保留现有模板；miss / 预约进入冷路径
- [x] 4.2 冷路径：算法轨固定 7 日（或快照）；语境史仅在日词/近况/规律线索时 TIME 解窗 → 拉史 → `build_feeding_history_prompt_blocks`
- [x] 4.3 样本够：LLM 注入原话+工具 JSON（+按需紧凑史）；提示词在 `prompts/system.py`；SSE `stream(thinking_enabled=True)`；禁止编造数字
- [x] 4.4 全程 MUST NOT 回落「上一次…用时」查史完成句
- [x] 4.5 纯「下次何时」类不拉语境史；有日词/最近/隔多久等才注入史
- [x] 4.6 语境史按命中事件收窄（叶=自身；父=其下叶）；不按根灌同根兄弟叶；不硬顶 1 日

## 5. 验收

- [ ] 5.1 手工：Go 有 imminent/active → 仍模板
- [ ] 5.2 手工：Go 空 + 近 7 日足够样本 → LLM 依据工具数字作答；连续追问不重复重算（TTL 内）
- [ ] 5.3 手工：样本不足 → 「数据量太少，无法预测」
- [ ] 5.4 手工：预约有/无 nextAt → 约定时间或无约定降级
- [ ] 5.5 手工：CUD 落库后快照失效，再问会重算
- [ ] 5.6 手工：纯「下一次配方奶是什么时候」不二次拉语境史；「最近隔多久」会拉史
- [ ] 5.7 手工：「最近配方奶…」语境史仅配方奶，不含同根其它喂养叶

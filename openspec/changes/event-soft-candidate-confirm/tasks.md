## 1. EVENT LLM 契约

- [x] 1.1 改 `SEGMENT_EVENT_LLM_PROMPT`：输出 `candidates[]`；删「禁止猜营养品 / 专名无把握必须空」；保留禁编造 id、禁新建类型；领域句保留
- [x] 1.2 `llm_resolve_event` 解析 candidates（兼容单 `event_id`）、过滤表外 id、截断 K≤3

## 2. Soft 出口与 pending

- [x] 2.1 `resolve_event` / `resolve_segment`：梯子 miss 后 LLM 有候选时写入 soft candidates，勿立刻 `event_unresolved`
- [x] 2.2 `resolve_segments` / `drafts_to_intent`：K=1 → `leaf_confirm`；K≥2 → 消歧 pending（复用 remark/parent）；K=0 → 无法识别
- [x] 2.3 predict 单候选话术：复述问法并点出候选事件名（如「你要问的是接下来几点钟吃辅食吗？」）；create/read 用既有确认模板点名

## 3. 确认后飞轮

- [x] 3.1 软确认/消歧点选成功后 `add_event_phrase`（核词优先 `remark_keyword_from_segment`）；reject 不写；禁止整句入飞轮

## 4. 验收

- [ ] 4.1 手工：「接下来几点钟吃午饭」→ 软确认辅食（非无法识别）→ 确认后可播报/估时
- [ ] 4.2 手工：确认后飞轮「午饭」→ 辅食；再问宜硬命中或少问
- [ ] 4.3 手工：多候选句出现 options 消歧；拒绝不写飞轮

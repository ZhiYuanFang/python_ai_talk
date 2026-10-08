## 1. 时长与起止抽取

- [x] 1.1 新增 duration 抽取（N分钟/N分 → 秒），不写入 quantity
- [x] 1.2 扩展 overlay：0/1 clock + duration → 闭合 start/end；无钟点用 now−dur / now
- [x] 1.3 扩展 overlay：恰好两 clock（起止）→ start/end，不降级；≥3 clock 且单条仍降级

## 2. 落库与提示

- [x] 2.1 `collect_event_items`：计时 create 在 end_time>0 时尊重，否则 end=0
- [x] 2.2 更新 classify system：开表 vs 闭合补记约定
- [x] 2.3 计时闭合时 action 避免误当成需开表的纯 start（与 collect/overlay 一致）

## 3. 手工验收

- [ ] 3.1 「早上8点母乳10分钟」→ 08:00–08:10，非进行中
- [ ] 3.2 「母乳10分钟」→ 约 now−10min～now
- [ ] 3.3 「8点到8点半母乳」→ 双钟点起止，缓存命中不因双钟点误降级
- [ ] 3.4 已有进行中母乳时补记闭合十分钟，batch 成功
- [ ] 3.5 「开始母乳」无时长仍 end=0；若已有进行中则仍「已在进行中」

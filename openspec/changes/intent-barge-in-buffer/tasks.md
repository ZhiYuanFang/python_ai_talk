## 1. 设备缓冲与单飞

- [x] 1.1 实现 deviceNo 级 barge store（busy、anchor、pending[]、rerun_count）；Redis TTL 600s；中文注释
- [x] 1.2 意图同步/流式入口：空闲占坑开跑；busy 则入缓冲并 await 本轮结束
- [x] 1.3 异常路径与 TTL：释放 busy、清缓冲

## 2. 终局判定与重跑

- [x] 2.1 复用 `infer_miss_fail_kind` 判定拼接触发；确认/消歧丢缓冲；「数据量太少，无法预测」不触发拼接
- [x] 2.2 miss 且有 pending：全量拼接 → 立刻清 pending → 重跑；rerun_count≤5
- [x] 2.3 占坑连接承载完整 SSE（含重跑 thinking）；挂起连接不重放 thinking，结束后回终答快照或合并 ack

## 3. 验收

- [ ] 3.1 手工：同 device 连续两 POST，仅一条思考流；第二条挂起后收到终答/合并
- [ ] 3.2 手工：首句无法识别 + 思考中补事件名 → 拼接重跑后可识别
- [ ] 3.3 手工：确认态 / 成功答 → 缓冲丢弃不重跑
- [ ] 3.4 手工：「数据量太少，无法预测」不拼接重跑

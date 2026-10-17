## 1. 先读 Go

- [x] 1.1 从 imminent 与 active-eta 匹配条目读取预计时长和预计用量，兼容 `expectDurationSec` / `expect_duration_sec` / `expectDuration` 与 `expectAmount` / `expect_amount`
- [x] 1.2 用量和用时在打本地间隔算法之前先按通道请求 Go；该格有数则播报且不拉近 7 日、不写入间隔快照
- [x] 1.3 没有条目、该格为空或接口失败时走现有间隔算法；何时模板与预约约定保持

## 2. 手工确认

- [ ] 2.1 「这次要睡多久」在 imminent 有预计时长时不再出现近 7 日 history filter
- [ ] 2.2 imminent 没有时长时仍走间隔算法；「还要多久」仍按剩余时间播报

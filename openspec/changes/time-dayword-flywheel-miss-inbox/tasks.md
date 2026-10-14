## 1. 日词本地规则前移

- [x] 1.1 段 TIME：仅日词无钟点 → `parse_day_word_window` 填窗；跳过 TIME LLM；不写 time rule_gap
- [x] 1.2 日词+钟点不得整日短路；保持槽位/飞轮/LLM 路径

## 2. 全轨时间飞轮

- [x] 2.1 去掉 read 轨 `allow_flywheel=False`；create/read/update/delete 同等读/写相对配方
- [x] 2.2 日词或飞轮命中后禁止再调 TIME LLM；仅 Unix 仍不进飞轮

## 3. 答不出 miss inbox

- [x] 3.1 新增独立 store（非 rule_gap / 非 time_cues）与 list/delete Admin API
- [x] 3.2 终局失败出口挂钩落库（无法识别 / other 暂不支持等）；确认中不写
- [x] 3.3 路由注册；中文注释

## 4. 验收

- [ ] 4.1 手工：「昨天拉了几次屎」→ 本地窗、无 TIME LLM、无 time 缺口
- [ ] 4.2 手工：相对时间句 read/create 均可飞轮命中免 LLM（有数据时）
- [ ] 4.3 手工：无法识别 → miss inbox 可见可删；确认问句不进箱

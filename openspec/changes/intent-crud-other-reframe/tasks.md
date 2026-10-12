## 1. 枚举与 OP 分轨骨架

- [x] 1.1 重定义顶层轨枚举为 create|read|update|delete|exit|other；清理 suggest/conversation/feeding/history/predict 主轨用法；中文注释
- [x] 1.2 段拆分后逐段判 OP；实现 SegmentOutcome + 整轮统一汇总话术
- [x] 1.3 other →「暂不支持」且不结束会话；exit 仍退出
- [x] 1.4 新增 OP 整段飞轮 store + admin（或演进 type-cache）；停用短关键词 TYPE 热路径

## 2. C 轨

- [x] 2.1 C：事件（整段/演进 intents）→ 时间规则（无时间飞轮；miss→TIME LLM→rule_gap）→ 数量（规则/QTY LLM→qty 飞轮）→ 缺槽追问
- [x] 2.2 按 one|number|time 组装 create 形态；time 无闭合追问
- [x] 2.3 映射进既有 batch 提交（一期）

## 3. R 轨

- [x] 3.1 R·source 整段飞轮（record|predict）；缺维走 LLM 并回写
- [x] 3.2 record：规则定窗 → 查史 → 整段播报飞轮（演进 history_speak）；接 speak 模板
- [x] 3.3 predict：channel/time_answer 整段飞轮 → active-eta / imminent → 播报；禁止回落「上一次用时」
- [x] 3.4 图路由：read 进 R，不再用顶层 history/predict 分叉

## 4. U / D 轨

- [x] 4.1 U/D 定位策略飞轮 + 查史选行；更新/删除经 batch（带 historyId）
- [x] 4.2 U·end：找仅 start 无 end；有则更新；无则转 C（复用 2.x）
- [x] 4.3 多候选无法唯一定位 → 段级 clarify，进统一汇总

## 5. 飞轮清理与种子

- [x] 5.1 数量飞轮 store + 接线；无量线索不写飞轮
- [x] 5.2 清空/迁移短关键词 type_cues 与 history_speak 短词种子；灌整句种子（睡着了/睡醒了/睡了多久了/还有多久醒来…）
- [ ] 5.3（兄弟仓）Hub 页对齐 OP/分层飞轮 admin

## 6. 验收

- [ ] 6.1 手工：复合句一段成功一段追问 → 一次汇总两边都有
- [ ] 6.2 手工：睡醒了有进行中 → U；无进行中 → C 且 time 无闭合则追问
- [ ] 6.3 手工：睡了多久了 → read+record；还有多久醒来 → read+predict
- [ ] 6.4 手工：other 暂不支持可续说；时间 miss 仍进 rule_gap；同口语量二次可飞轮跳过 QTY LLM

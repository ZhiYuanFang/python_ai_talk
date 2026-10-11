## 1. 拼装与管线门控

- [x] 1.1 `drafts_to_intent` / `resolve_segments`：成功且无缺量等阻塞时 `need_confirm=false`；失败/闲聊逻辑不变
- [x] 1.2 `intent_pipeline`：去掉「`match_source==llm` 一律 leaf_confirm」；无阻塞时直接 `_execute_after_confirm`（或等价）
- [x] 1.3 多段无阻塞：一次或按路径直接执行，不再拼 yes/no 确认问句

## 2. 飞轮与验收

- [x] 2.1 短说法写入改到落库/查史执行成功之后（按段）；失败不写
- [ ] 2.2 手工：睡醒了直结束回执；吃了120奶直落库；缺量仍追问；父消歧仍问

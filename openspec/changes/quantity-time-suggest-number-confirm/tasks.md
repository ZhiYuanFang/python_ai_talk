## 1. 分类提示词

- [x] 1.1 在 `INTENT_CLASSIFICATION_SYSTEM_TEMPLATE` 增加通用规则：有 quantity 且口语会落 time 时，由 LLM 在表内找近义 number 叶并改选；禁止把 quantity 记到 time 叶；时长（N分钟）不触发
- [x] 1.2 约束冲突改选时 `confirm_message` 为简洁确认句（示例：「您是要记录瓶喂母乳60毫升嘛？」），禁止冗长解释/多选项列表；reasoning 须中文并核对 type
- [x] 1.3 约定无近义 number 时不编造事件，可保持 time 叶原确认路径

## 2. 确认话术传递

- [x] 2.1 核对 classify → `intent_pipeline` → `create_leaf_confirm_pending`：非空 `confirm_message` 须进入 pending 可见话术
- [x] 2.2 确认仅当 `confirm_message` 为空才回退 `build_leaf_confirm_message`；冲突改选场景不得无条件覆盖 LLM 问句

## 3. 手工验收

- [x] 3.1 「记录60毫升母乳」→ 确认目标为瓶喂母乳（或表内近义 number）+ 简洁问句含毫升，非计时母乳直接确认落库
- [x] 3.2 「母乳10分钟」→ 仍可走计时母乳，不因本规则改选计量叶
- [x] 3.3 用户否定确认后仍可用 correct 改到其它叶（抽检路径未断）

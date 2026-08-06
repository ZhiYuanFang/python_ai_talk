## 1. 会话元数据

- [x] 1.1 扩展 `LastSuggestion`：增加 `history_grounded`、`qa_match_id`；序列化/反序列化兼容缺省（缺省 `history_grounded` 按 true）
- [x] 1.2 扩展 `append_turn` 入参并写入上述字段；补充中文注释

## 2. 写侧 promote 收紧

- [x] 2.1 `promote_accepted_qa` / `maybe_apply_implicit_feedback`：仅当 `history_grounded is False` 且 accepted + 有改写时入库；缺失字段不 promote
- [x] 2.2 clinic / intent clinic 写会话时传入本轮 `history_grounded`（由 `needs_history` / `force_needs_history` 推导）

## 3. 读侧拒绝禁捷径与问答降分

- [x] 3.1 `implicit_feedback`：判定 `rejected` 时向 state 写 `block_fast_path=true`；`unclear`/`accepted` 不因此置位
- [x] 3.2 `rejected` 且 `qa_match_id` 非空时下调该问答质量分；在 `vector_store` 增加问答集合质量更新方法（中文注释）
- [x] 3.3 clinic 捷径命中写会话时传入 `qa_match_id`

## 4. clinic 提示词分叉（口径 B）

- [x] 4.1 `clinic_answer` 系统提示与收尾按 `needs_history` 分叉：true 保留有据点名；false 去掉喂养/对话点名硬约束并禁止编造
- [x] 4.2 `needs_history=false` 时用户消息不注入喂养记录块、不注入 `chat_context` 块；生成节点传入门禁结果
- [x] 4.3 确认 tip 提示词与 tip 写会话路径未误改（仍可点名近史；不写 standalone / 不 promote）
- [x] 4.4 无史路径提示词增加收尾「征求家长肯定本段回应」（口语一句，非问卷）

## 5. 校验与收尾

- [x] 5.1 `openspec validate tighten-qa-flywheel-no-history --strict` 通过
- [x] 5.2 自检：拒绝后本轮不走捷径；无史 accepted 可入库；有史 accepted 不入库

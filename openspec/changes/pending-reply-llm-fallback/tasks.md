## 1. Hard-match normalization

- [x] 1.1 在 `clarification.py` 增加回复归一化（strip、剥句末 `。．.!！?？`、英文 casefold）
- [x] 1.2 将 `resolve_free_text` 硬匹配路径改为使用归一化文本（名称/序号/拒绝/肯定）
- [x] 1.3 覆盖用例：`是的。` 在 `leaf_confirm` 下硬匹配成功且不调 LLM

## 2. Resolve model & LLM clarify prompt

- [x] 2.1 扩展 `ResolveResult`（或并列结构）以支持动作：`confirm`/`select`/`correct`/`reject`/`new_intent`/`ask_again`，以及可选 `quantity`、`event`
- [x] 2.2 新增澄清解析 system/user prompt（注入 kind、问句、options、原话；约束父消歧禁止裸 confirm）
- [x] 2.3 实现 `llm_resolve_pending_reply`：调用 `llm_client`，解析 JSON；超时/坏 JSON/缺动作 → `ask_again`

## 3. Pipeline wiring

- [x] 3.1 将 `resolve_free_text` / `try_handle_pending`（及路由调用点）改为 async，硬匹配 miss 后 await LLM
- [x] 3.2 处理 `confirm`/`select`：quantity 覆盖 pending 后按现有叶子落地与飞轮逻辑收尾
- [x] 3.3 处理 `correct`：叶子则直接落地；父则创建 `parent_disambiguation`；非法事件 id → `ask_again`
- [x] 3.4 处理 `reject` / `new_intent` / `ask_again` 与 LLM 失败回退（失败保持 pending）
- [x] 3.5 飞轮：最终叶子落地写 `original_utterance`；correct/否定路径不对旧 `matched_vector_id` 做 `success_count++`

## 4. Verification

- [x] 4.1 回归：`是的。`；`是的，喂了30毫升`（qty 覆盖）；`不是的，是<叶子>` 直落
- [x] 4.2 回归：纠正到父 → 新消歧；父消歧下裸「是的」→ ask_again；离题 → new_intent
- [x] 4.3 回归：模拟 LLM 超时/坏 JSON → 保持 pending 再问

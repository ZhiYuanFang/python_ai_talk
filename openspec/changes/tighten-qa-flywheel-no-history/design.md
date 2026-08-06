## Context

clinic 已具备：`needs_history` 门禁、独立问句改写、全局 `qa_fast_path` 命中跳过生成 LLM、隐式三态采纳驱动通识质量分与（accepted 时）问答入库。探索结论是：飞轮应沉淀「可跳过生成 LLM」的通识问答，而非绑定本机史/对话的整段答；成功标准是跳过 clinic 生成 LLM。用户选定口径 **B**：无史路径连陪伴对话点名也关闭。

## Goals / Non-Goals

**Goals:**

- 写侧：仅无史接地（`needs_history=false`）且 accepted + 成功改写时 promote Q→A。
- 读侧：`rejected` 禁止本轮 Q&A 捷径，强制完整生成以纠正幻觉。
- 捷径答被拒时下调该 `qa` 条目质量分。
- clinic 生成提示词按 `needs_history` 分叉；false 时不要求点名喂养史，也不要求点名陪伴对话（B）。
- `last_suggestion` 持久化史接地标志与可选 `qa_match_id`。

**Non-Goals:**

- 不改 tip 开场「有近史则点名」行为；tip 仍不写 `standalone_question`、不进 Q&A 推广。
- 不追求本轮「零 LLM」（改写 LLM 可保留）；KPI 是跳过 **clinic_answer 生成 LLM**。
- 不做历史脏 Q&A 全量清洗脚本（可后续运维）；本变更保证新写入与拒答降分。
- 不新增对外 HTTP API。

## Decisions

### D1: promote 以会话上持久化的 `history_grounded` 为准

Promote 发生在下一轮 `implicit_feedback`，图状态中已无上轮 `needs_history`。因此在 `append_turn` 时写入 `last_suggestion.history_grounded = (needs_history == true)`（或等价命名）。`history_grounded=true` 时即使 accepted 也不调用 `promote_accepted_qa`。

**Alternatives:** 同步在生成当轮 promote（无隐式采纳信号）— 拒绝，质量不可控。

### D2: 仅 `rejected` 禁捷径；`unclear` / `accepted` / 无上条允许

用户目标是「否认后重生成」。`unclear`（换话题）仍允许捷径，避免拖慢通识追问。实现：`implicit_feedback` 在判定为 `rejected` 时向 state 写 `block_fast_path=true`（已有钩子）。

**Alternatives:** 「非 accepted 一律禁」— 过严，拒绝。

### D3: 口径 B — 无史路径关闭对话点名

当 `needs_history=false`：clinic 系统提示与收尾 **SHALL NOT** 要求点名喂养记录或近期陪伴对话；用户消息构建 **SHALL NOT** 注入喂养记录块；`chat_context` 可不注入，或注入但不附「必须点名」指令（推荐：**不注入 chat_context 块**，避免模型自发复述私货，保证入库答可全局复用）。无史路径收尾 **SHALL** 轻轻征求家长是否认这段回应（口语一句，非问卷），便于下一轮隐式 accepted/rejected。当 `needs_history=true`：保持现有有据点名（史必点；对话若注入则点名），不强制「征求肯定」收尾。

**Alternatives:** A（仅关喂养点名、保留对话点名）— 用户已选 B。

### D4: 捷径命中写入 `qa_match_id`；拒绝时更新问答质量

`qa_hit` 路径 `append_turn` 写入 `last_suggestion.qa_match_id`。下一轮 `rejected` 时对应该 id 调用问答集合质量下调（与通识 `update_quality_score` 语义类似，可新增 `update_qa_quality_score`）。`knowledge_ids` 通识飞轮逻辑不变。

### D5: 提示词分叉放在 clinic_answer 构建，键为 `needs_history`

`build_clinic_answer_system_prompt(needs_history: bool)` / user message 构建读取 state 的 `needs_history`。点查/汇总规则仅在有史（或 `force_needs_history`）路径保留。intent 的 `call_clinic_agent` 共用同一构建函数。

## Risks / Trade-offs

- [无史路径续聊黏性下降] → Mitigation：仍保留引导式收尾与闺蜜语气；多轮温度不靠复述「上次你说」。
- [门禁偏 true → 可入库量少、捷径升温慢] → Mitigation：接受「宁缺毋滥」；质量优于命中率。
- [旧库已有脏 Q&A] → Mitigation：拒答降分 + quality 门槛；可选后续清理，非本变更阻塞。
- [改写仍耗 LLM] → Mitigation：接受；文档化 KPI 为跳过生成 LLM，非零 LLM。

## Migration Plan

1. 部署代码：新字段缺省兼容旧 Redis JSON（`history_grounded` 缺省视为 true 以保守不 promote；或缺省 false 仅当明确 false 才 promote——**采用：缺省 true（不 promote）更安全**）。
2. 回滚：关闭 `qa_fast_path_enabled` 或回退版本；会话多数字段可忽略。

## Open Questions

- 无史路径是否完全不注入 `chat_context` 文本块（推荐是），或仅去掉点名指令但仍注入——实现默认：**不注入块**。若产品后续要弱续聊，可再放开「注入但不点名」。

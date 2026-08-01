## Context

tip / clinic HTTP 已共享 Redis 陪伴会话（`device_no`、近 N 轮、`chat_context`、隐式飞轮、`clinic_answer` 闺蜜人格）。Intent 在 `conversation` / `suggest` 时走 `call_clinic_agent`：同进程 `clinic_graph.ainvoke` + `generate_response`（history/suggest 旧提示词），**不读不写** companion session，也不跑飞轮。产品要求 A+B+C+D 全做，把该路径纳入同一时间线。

约束：会话主键仍仅为 `device_no`；与 intent `conversation_id`（pending）无关；feeding / history / pending 短路径不碰会话。

## Goals / Non-Goals

**Goals:**

- `call_clinic_agent`：**读** session → `chat_context`；**写** `append_turn` + `last_suggestion`
- 生成前：**隐式飞轮**（与 clinic 同语义：三态、accept/reject 调分、成功标记 applied；失败可重试不阻断）
- 生成：**闺蜜 `clinic_answer` 同步路径**（与 stream 同 system/user 拼装，invoke 非 SSE）
- knowledge ids 与进 prompt 的 knowledge 对齐，供飞轮

**Non-Goals:**

- 不改 tip/clinic HTTP 契约与主流程（除多一方读写同一 key）
- 不把 intent SSE 改成逐步 clinic 节点 thinking（可保持整段 `call_clinic_agent` 一条 thinking）
- 不强制 intent 全量改走 `/clinic/stream` HTTP
- 不扩大到 feeding / history 写陪伴轮次

## Decisions

### 1. 改动落点：增强 `call_clinic_agent`，不新开 HTTP

- **选择**：在现有节点内编排飞轮 → 读会话 → clinic_graph → 闺蜜同步生成 → append_turn
- **理由**：stream/非流式 intent 都已调用该节点；一处改两端受益
- **备选**：路由层包装 → 重复、易漏 ainvoke 路径

### 2. 生成：复用 `clinic_answer` + `llm_client.invoke`

- **选择**：抽或内联与 `stream_response` 相同的 prompt 拼装，改为 `invoke` 拿全文；`conversation`/`suggest` 均走闺蜜（suggest 仍可带知识/画像进同一模板）
- **理由**：满足 D；避免维持两套人格
- **备选**：继续 `generate_response` 仅塞 `chat_context` → 旧提示词无闺蜜字段，D 失败
- **注意**：`generate_response` 仍服务 intent **history** 短链，本 change 不删

### 3. 飞轮：复用 `judge_suggestion_acceptance` + `apply_flywheel_for_status`

- **选择**：逻辑对齐 clinic `_maybe_apply_implicit_feedback`（可抽 shared 小函数减少重复）
- **理由**：C 与 clinic 一致；intent 用户句 = `user_input`
- **顺序**：飞轮 → 读会话（applied 后 last_suggestion 已标）→ 数据准备 → 生成 → 写新轮

### 4. `source` 取值

- **选择**：`append_turn` / `last_suggestion.source` 使用 `"intent"`
- **理由**：与 tip/clinic 区分，便于排查；截断与飞轮不依赖 source 枚举

### 5. 失败与写会话

- **选择**：兜底文案仍返回结构化 intent；**兜底不写** `append_turn`（或仅成功非空真实回答才写）。飞轮异常不阻断。会话写失败只打日志，不改 intent 响应
- **理由**：避免把 CLINIC_FALLBACK 当成可飞轮建议污染质量分

### 6. chat_context 注入时机

- **选择**：构造 `clinic_state` 时写入 `chat_context`（读自 Redis）；生成时再读 state 中的字段（与 clinic stream 一致）
- **理由**：clinic_state / tip_state 已声明该字段；数据准备节点不消费它也无害

## Risks / Trade-offs

- [intent 多一次飞轮 LLM] → 与 clinic 同成本；仅有未 applied suggestion 时触发
- [双端同时写 Redis] → 现 store 已整包读写；极端并发可能丢一轮，接受与 tip/clinic 相同风险
- [history 仍旧提示词] → 有意 Non-Goal；勿误改 history 短链
- [suggest 与闺蜜模板合一] → 语气统一为陪伴；若产品要「更建议感」可后续在 clinic_answer 内按 target 微调，不单开旧 suggest prompt

## Migration Plan

1. 部署后：tip → intent conversation → clinic，应能互相看见近轮对话
2. 回滚：恢复旧 `call_clinic_agent`（不读写会话、走 generate_response）即可

## Open Questions

- 无（A/B/C/D 已确认全做）

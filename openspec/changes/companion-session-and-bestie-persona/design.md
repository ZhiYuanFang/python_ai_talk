## Context

clinic / tip 今天各自无对话状态：请求体只有问题或事件信息，图内拉取的是喂养 `history_events`，不是 tip↔clinic 聊天轮次。知识飞轮依赖前端显式 `/feedback`（👍/👎），而产品已去掉「建议是否采纳」操作。人格提示词仍为「儿科医生助手 / 育儿助手 + 注意事项清单」。

约束：不删 HTTP 入口；feeding 与 clinic 不可互引共享逻辑须放 `app/shared`；本仓已用 Redis 做 `RedisGate`，会话复用同一 Redis；Python 为 Go 调用的智能内核。

## Goals / Non-Goals

**Goals:**

- 按 `device_no` 在 Python Redis 中维护 tip/clinic 共享陪伴会话（5 轮、TTL 7 天）
- tip 开场与 clinic 续聊注入近 5 轮上下文，隔天仍可续（未过期）
- clinic 下一轮对上一条建议（含 tip 开场）做接受/拒绝/说不清判定并驱动飞轮
- tip/clinic/suggest 面向用户输出改为口语化闺蜜人格（对家长）

**Non-Goals:**

- 删除或重命名 `/v1/clinic/*`、`/v1/tip/*`、knowledge、health
- 按事件/会话 ID 多分房（主键仅 `device_no`）
- 改造 intent pending 澄清存储（仍可保持进程内）
- 替换知识库内容本身（继续用喂养知识当背景）
- 强制 Go/Flutter 同步改路径（契约可渐进）

## Decisions

### 1. 会话主键与存储

- **选择**：Redis key 形如 `companion:session:{device_no}`；值为 JSON（turns、last_suggestion、updated_at）
- **理由**：产品确认单设备一条陪伴线；跨天/多副本必须落 Redis，不能用 intent 的内存 `clarification_store`
- **备选**：`device_no + conversation_id`（更灵活，但前端/Go 要多传字段，本次不采用）；纯前端透传 messages（无法保证隔天、多端一致）

### 2. 「5 轮」与 tip 开场结构

- **选择**：一轮 = 一条 user + 一条 assistant。tip 开场写入时合成 user 文案（如「刚记录了「{event_name}」」）+ assistant=tip 全文，占 1 轮；截断时丢最旧整轮
- **理由**：截断与计数规则统一，避免「只有 assistant 的半轮」特判
- **备选**：tip 只存 assistant，截断按 message 条数（更省字但轮次语义乱）

### 3. TTL 与续期

- **选择**：TTL 7 天；每次成功读写后 `EXPIRE` 滑动续期
- **理由**：产品指定 7 天；滑动续期符合「还在聊就别过期」

### 4. 上下文注入位置

- **选择**：在 tip/clinic **路由层**读会话，把近 5 轮格式化进生成提示词（user message 或独立「近期对话」块）；图内 `judge_data_requirement` / `fetch_history` 仍只管喂养数据，不把聊天当喂养史
- **理由**：省 token 的产品动机是「喂养史已有 judge」；聊天窗口小且固定，不必进 judge LLM
- **备选**：把 chat 塞进 clinic_graph State 新节点（更重，收益小）

### 5. 隐式飞轮判定

- **选择**：clinic（及若需要 tip 之后的第一句 clinic）在生成前调用轻量判定（规则启发 + 小 LLM JSON：`accepted|rejected|unclear`）；仅当 `last_suggestion.feedback_applied == false` 且存在待判定建议时执行；`accepted`→对 `knowledge_ids` +1，`rejected`→-1，`unclear`/失败→不改分并仍可标记已处理或保留待下次（默认：**unclear/失败不标记 applied**，仅成功 ±1 后标记，避免永久卡住——折中：**三态都标记 applied**，unclear 不改分，避免重复判同一条）
- **定稿折中**：三态判定完成后均置 `feedback_applied=true`；仅 accepted/rejected 调 `update_quality_score`；失败（异常）不置位，下次可重试
- **理由**：前端无按钮；tip 开场算待判定建议；每条只飞轮一次
- **知识 ID**：写 `last_suggestion` 时保存本轮向量检索命中的真实 `doc_id` 列表（修复/绕开用 `answer_id` 当 doc_id 的问题）；无 knowledge 时跳过飞轮加减分但仍可清空待判定

### 6. 人格提示词

- **选择**：改写 `clinic_answer`、`tip_answer`、`suggest_answer`（及必要时 history/conversation 共用路径）system + 输出要求：对家长「你」、娃称「宝宝」；先接情绪再顺嘴带信息；禁止说明书式强制 `## 注意事项`；保留「不诊断、不开药、真担心温柔劝就医」
- **理由**：接口与图不动，人格切换成本最低且与会话轨正交

### 7. 模块归属

- **选择**：`app/shared/companion_session.py`（或 `services/companion_session_store.py`）+ `app/shared/suggestion_acceptance.py`（判定）；tip/clinic 路由调用；禁止 tip↔clinic 互引
- **理由**：符合 project 目录约束

### 8. 显式 feedback API

- **选择**：保留 `/v1/clinic/feedback`、`/v1/tip/feedback`；主路径不依赖它们
- **理由**：兼容旧客户端；避免 **BREAKING**

## Risks / Trade-offs

- [单设备一把钥匙] → 新 tip 开场挤进同一会话并顶掉旧轮；接受「闺蜜一条线」。若以后要分事件房间，需改主键
- [隐式判定误伤飞轮] → 三态 + unclear 不改分；失败可重试；仅对真实 knowledge_ids 加减分
- [Redis 与 project 文档「不直连 Redis」表述冲突] → 与现网 `RedisGate` 一致，会话复用同一客户端工厂；文档可在后续澄清
- [feeding 已 import clinic（call_clinic_agent）] → 本变更不扩大该违规面；人格改 suggest 时在 clinic 提示词侧改即可
- [5 轮仍可能偏长] → 截断 + 口语短答；喂养史不重复塞满聊天
- [多副本竞态] → 同一 device 并发 tip+clinic 可能交错；可用短 Redis WATCH/Lua 或「读-改-写带 updated_at」尽最大努力，不要求强事务

## Migration Plan

1. 部署含会话与新提示词的 Python 版本；无会话时行为退化为今日单轮（兼容）
2. Go/Flutter 无需改路径；续聊只要继续传同一 `device_no`
3. 回滚：关掉会话读写开关（若加 feature flag）或回滚版本；Redis key 自行过期；显式 feedback 仍可用

## Open Questions

- tip 合成 user 文案的最终中文模板是否需产品审定（实现可用默认「刚记录了「{event_name}」」）
- 滑动续期是否在「仅读会话展示」时也续期（若未来有 GET；当前仅 tip/clinic 写路径续期即可）
- intent 主路径 conversation 是否必须注入 companion 会话（建议 **本期不注入 intent**，避免与 feeding 澄清会话搅在一起；仅统一 suggest/clinic 提示词人格）

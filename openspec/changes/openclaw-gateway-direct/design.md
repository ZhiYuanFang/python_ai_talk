## Context

当前进行中的 `openclaw-three-agents` 已删除 tip、对齐四 REST/top_k、引入飞轮门面，但编排仍是 Python 自写 `run_agent_steps`，`OPENCLAW_GATEWAY_URL` 为空。Go 经 `PythonAIClient` 调用 `/v1/analyze|clinic|care-alert`，并仍转发 clinic/care 反馈到 Python 飞轮。探索结论要求：**真实 OpenClaw Gateway 直接对外**；Go 零飞轮；Care 不做飞轮；Clinic 无显式点赞。

利益相关：Python AI Talk、go_ai_talk、OpenClaw Gateway 运维、Flutter（反馈 UI 收缩）。

## Goals / Non-Goals

**Goals:**

- Gateway 成为 Intent / Clinic / Care Alert 唯一编排权威。
- Go：鉴权、额度、**注入 model**、调用 Gateway、播 reply / 取 Care 卡片 tool result；日缓存仅展示语义。
- Intent：tool 落库 + NL reply；删除结构化意图信封。
- 飞轮：仅 Intent + Clinic；仅 agent→飞轮 tool；Go 配置与代码零飞轮。
- Care：Gateway + 结构化出卡；无飞轮。
- Clinic：仅 agent 内隐式采纳；删除显式 feedback 路由。

**Non-Goals:**

- 不恢复 tip SSE / tip agent。
- 不在本变更实现完整 OpenClaw 集群高可用运维手册（须能本机/compose 跑通单 Gateway）。
- 不强制 Flutter 全部视觉改版（删除死反馈调用即可）。
- 不保留「进程内迷你图」作为长期兼容层。
- 禁止生成测试文件。

## Decisions

### D1：入口形态 = Gateway 直接对外（方案 2）

- **选择**：Go 打 OpenClaw Gateway（WS RPC `agent`/`sessions` 或经网关反代）；废 Python 大半 FastAPI 编排入口。
- **替代**：FastAPI 代理 Gateway → 仍多一层伪内核，拒绝。
- **原因**：用户明确不要自编排；产品未上线可 BREAKING。

### D2：Go 注 model，Gateway 跑 loop

- **选择**：`ResolveLaneModel`（或等价）在进 Gateway **前**完成；per-run 传入 Gateway（如 model override / run 参数）。成功返回后再计次。
- **替代**：Gateway 自管选模 → 与现有 VIP/额度模型冲突。
- **原因**：商业逻辑留 Go；智能编排留 Gateway。

### D3：Intent = tools 写库 + 纯 reply

- **选择**：删除 `AnalyzeIntentResponse` 类结构化契约；澄清靠 Gateway session，不靠 `need_confirm`。
- **替代**：强制最终 JSON tool → 仍是结构化契约换皮，拒绝。
- **原因**：落库权威在 tool；Go 只播话术。

### D4：飞轮隔离与仓收缩

- **选择**：Go 零飞轮；Care **无**飞轮；Clinic **无**显式赞，仅隐式采纳在 Clinic agent 内调飞轮 tool；Intent 成功写后由 Intent agent 调飞轮 tool。
- **替代**：Go 转发反馈 → 违反零飞轮；前端直打 Python → 禁止。
- **原因**：护城河在我方 agent/tool 闭环，不在业务壳。

### D5：Care 出卡 = 结构化 tool result

- **选择**：`emit_care_cards`（名可调）返回 items[]；Go 从 run 的 tool 结果取数写入日缓存；assistant 自由文本不是卡片权威。
- **替代**：解析 reply JSON → 脆弱，拒绝。

### D6：与 `openclaw-three-agents` 关系

- **选择**：本变更为权威后续；继承 tip 删、四 REST、top_k、飞轮门面代码资产；作废「进程内 loop = OpenClaw」；apply 时可先停旧 change 验收 10.1–10.3（按旧 FastAPI），改按本 tasks 验收。
- **替代**：改写旧 change 到底 → 叙事混乱。

### D7：Python 残留面

- **选择**：飞轮 HTTP tools（intent retrieve/record、clinic record/retrieve）；可选知识检索 tool。History CRUD tools **直打 Go** REST。删除 care 飞轮模块与 clinic/intent 编排路由。
- **替代**：Python 继续转 history → 多余跳数。

## Risks / Trade-offs

- **[Intent 误写]** 无结构化确认门闩 → Mitigation：skill 要求低置信只追问不写；写 tool 侧校验必填字段；接受未上线期试错。
- **[Gateway API 选型]** WS RPC vs OpenAI 兼容 HTTP → Mitigation：spike 锁定；优先官方 external-apps / agent.run；sessionKey 稳定映射 device/conversation。
- **[Care 无飞轮]** prompt 不再越用越准 → Mitigation：接受；卡片靠当日 history 现算。
- **[跨仓工作量大]** → Mitigation：tasks 分 Python / Go / Gateway / Flutter；先 Intent 通路再 Clinic/Care。
- **[旧迷你 runtime 残留]** → Mitigation：tasks 明确删除 `shared/agents/runtime.py` 与各 `*_agent.py` 编排，禁止留兼容壳冒充 Gateway。

## Migration Plan

1. Spike：本机 Gateway + Go 注 model 跑通一轮 Intent（假 tool → 真 filter）。
2. 注册三 agent + tool ACL；飞轮 tools（无 Care）。
3. Go 切 Intent 客户端；删结构化解析；Python 删意图入口。
4. Clinic Gateway + 隐式采纳；删显式 feedback。
5. Care Gateway 出卡；删 Care 飞轮与 Go 转发。
6. 收束 FastAPI；更新 `project.md` 技术栈为真实 Gateway。
7. 回滚：未上线，git revert + 关 Gateway 旁路；无生产数据迁移。

## Open Questions

- ~~Gateway 具体发行版与 Go 客户端（官方 SDK / 自研 WS）在 apply 首个 spike 锁定并写入本 design 附录。~~ → 见附录 A。
- Intent sessionKey 格式：`deviceNo` 单键 vs `deviceNo:threadId`（默认：`intent:{deviceNo}`，澄清续轮同键）。→ **已锁定**：`intent:{deviceNo}`；Clinic=`clinic:{deviceNo}`；Care 日批=`care:{deviceNo}:{day}`。
- Clinic 隐式采纳判定：继续用现有 LLM 三态逻辑迁入 skill/tool，或简化启发式（默认：**迁入 Gateway 侧可调用的判定 tool**，实现可复用现有 Python 函数经飞轮服务暴露）。→ **已锁定**：Python 飞轮服务暴露 `clinic.judge_implicit_acceptance` + `clinic.record_outcome` tools，由 Clinic agent 在回合内调用。

## 附录 A：Spike 锁定（任务 1.1）

**日期**：2026-08-15  
**发行版**：`openclaw@2026.7.1-2`（npm latest 当时版本；compose 钉死该 tag）。  
**运行时要求**：Node.js `>=22.22.3 <23` 或 `>=24.15.0 <25` 或 `>=25.9.0`（本机曾为 v22.22.0，须升级后方可跑 Gateway）。

### Go 调用方式（锁定）

- **主路径**：Gateway **OpenAI 兼容 HTTP** `POST {OPENCLAW_GATEWAY_URL}/v1/chat/completions`（须配置 `gateway.http.endpoints.chatCompletions.enabled: true`）。
- **原因**：Go 原生 http 客户端即可；无需 Node `@openclaw/gateway-client` 设备配对；与现有额度/注 model 对齐成本最低。
- **Agent 路由**：`model` 字段用 agent 目标 id：
  - Intent → `openclaw/intent`
  - Clinic → `openclaw/clinic`
  - Care Alert → `openclaw/care_alert`
- **注 model**：请求头 `x-openclaw-model: <provider/model>`（Go 在 `ResolveLaneModel` 后注入；Bearer token 模式具备 operator 全权）。
- **Session**：请求头 `x-openclaw-session-key: intent:{deviceNo}`（或上表）；勿用保留前缀 `subagent:`/`cron:`/`acp:`。
- **鉴权**：`Authorization: Bearer {OPENCLAW_GATEWAY_TOKEN}`；Gateway `gateway.auth.mode=token`。
- **流式**：`stream: true` → SSE，映射到现有 thinking/reply 产品帧。
- **备选（非主路径）**：WS RPC `agent` + device pairing（适合仪表盘；本仓 Go 业务壳不采用，除非 HTTP 能力不足）。

### Tool 结果（Care 卡片）

Care 出卡权威为 Gateway 内部 agent tools 的执行结果。Go 若需结构化 items：优先在同一 HTTP 回合用 OpenAI `tools`/`tool_calls` 客户端工具环，或 Gateway 侧 skill 将 `emit_care_cards` 结果写入约定旁路；**首版**：Care agent 系统提示强制最后调用 `emit_care_cards`，Go 解析非流式响应中的 `tool_calls` / 或开启 stream 收集 tool 事件（实现阶段按 OpenClaw 实际 tool 事件能力选型，见 tasks 3.4）。

### 本机 Spike 结果（任务 1.2 / 1.3，2026-08-15）

- Node：`v24.15.0`（满足 OpenClaw 要求）；CLI：`OpenClaw 2026.7.1-2`。
- Gateway：`openclaw gateway run --port 18789` 已 ready；`GET /v1/models` + Bearer token 返回 `openclaw` / `openclaw/default` / `openclaw/main`。
- Session：请求头 `x-openclaw-session-key: intent:spike-device` 时日志出现 lane `session:agent:main:intent:spike-device`（续轮键可用）。
- 注 model：支持头 `x-openclaw-model`（spike 曾试 `ollama/llama3.2`；完整 assistant reply 依赖本机已配置的 provider 密钥，不阻塞客户端契约锁定）。
- 三 agent 草稿：见仓库 `deploy/openclaw/openclaw.json5` 与 `docker-compose.openclaw.yml`（`agents.entries` 须按 doctor 校验后再启用；spike 先用 default agent 验证 HTTP）。

升级/启动备忘：

```bash
openclaw gateway run --port 18789 --force
curl -sS http://127.0.0.1:18789/v1/models -H "Authorization: Bearer $OPENCLAW_GATEWAY_TOKEN"
curl -sS http://127.0.0.1:18789/v1/chat/completions \
  -H "Authorization: Bearer $OPENCLAW_GATEWAY_TOKEN" \
  -H "Content-Type: application/json" \
  -H "x-openclaw-model: <provider/model>" \
  -H "x-openclaw-session-key: intent:spike-device" \
  -d '{"model":"openclaw/default","messages":[{"role":"user","content":"hi"}]}'
```

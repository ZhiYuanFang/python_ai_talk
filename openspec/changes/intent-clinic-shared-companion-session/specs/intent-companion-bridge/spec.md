## ADDED Requirements

### Requirement: Intent clinic agent reads companion chat context

当意图路径执行 `call_clinic_agent` 时，系统 SHALL 按 `device_no` 读取与 tip/clinic 相同的陪伴会话，并将格式化后的近轮对话注入 `chat_context`（轮次上限与配置一致）。

#### Scenario: Prior tip turn is visible to intent clinic agent

- **WHEN** 该 `device_no` 已有 tip/clinic 写入的陪伴轮次，且意图路由到 `call_clinic_agent`
- **THEN** 生成所用上下文 SHALL 包含这些轮次（受 max_turns 截断约束）

#### Scenario: Empty session still proceeds

- **WHEN** 该 `device_no` 无陪伴会话或 turns 为空
- **THEN** `call_clinic_agent` SHALL 仍完成数据准备与生成（`chat_context` 可为空）

### Requirement: Intent clinic agent writes companion turn after success

`call_clinic_agent` 在成功生成非兜底回答后，SHALL 将本轮 `user_input` 与助手回答 `append_turn` 到同一 companion session，`source` 标识为 intent 路径，并更新 `last_suggestion`（含回答文本与本轮用于飞轮的 knowledge ids）。

#### Scenario: Successful reply is shared with clinic

- **WHEN** `call_clinic_agent` 成功返回真实回答
- **THEN** 随后同一 `device_no` 的 clinic/tip 读取会话时 SHALL 能看到该轮 user+assistant

#### Scenario: Fallback does not pollute session

- **WHEN** clinic agent 失败或仅返回兜底文案
- **THEN** 系统 SHALL NOT 将兜底内容作为新的陪伴轮次 / `last_suggestion` 写入（或等价：不更新 last_suggestion 供飞轮）

### Requirement: Implicit feedback before intent clinic generation

在 `call_clinic_agent` 生成回答之前，若会话存在未 `feedback_applied` 的 `last_suggestion`，系统 SHALL 对当前 `user_input` 与该建议做接受/拒绝/说不清三态判定；accept/reject 时更新知识质量分；判定成功（含 unclear）后标记 `feedback_applied`。判定失败 SHALL NOT 阻断主流程，且 MUST NOT 错误标记为已 applied。

#### Scenario: Follow-up intent accepts prior tip suggestion

- **WHEN** tip 开场留下未飞轮建议，用户经 intent conversation/suggest 追问且判定为 accepted
- **THEN** 相关 knowledge 质量分 SHALL 按接受规则更新，且该建议标记为已 applied

#### Scenario: Classifier failure skips mark

- **WHEN** 三态判定调用失败返回空
- **THEN** `feedback_applied` SHALL 保持 false，且主流程继续生成

### Requirement: Intent clinic agent uses bestie clinic_answer generation

`call_clinic_agent` 的最终回答生成 SHALL 使用与 `/clinic/stream` 一致的闺蜜陪伴提示词（`clinic_answer`），并纳入 `chat_context`、喂养史、知识与宝宝画像等 clinic 数据准备结果；SHALL NOT 再对 conversation/suggest 使用 `generate_response` 的 history/suggest 旧提示词路径。

#### Scenario: Conversation uses companion persona

- **WHEN** `target_type` 为 conversation 且进入 `call_clinic_agent`
- **THEN** LLM 系统/用户消息 SHALL 按闺蜜陪伴模板构建（含可选 chat_context 块）

#### Scenario: Suggest also uses companion persona

- **WHEN** `target_type` 为 suggest 且进入 `call_clinic_agent`
- **THEN** 生成 SHALL 同样走闺蜜 `clinic_answer` 路径（可携带知识/画像），而非旧 suggest_answer 专用路径

### Requirement: Non-clinic intent paths leave companion session untouched

feeding、history 短链、pending 澄清及精确父名消歧等未执行 `call_clinic_agent` 的路径，SHALL NOT 因本能力读写陪伴会话。

#### Scenario: Feeding record does not append companion turn

- **WHEN** 意图结果为 feeding 且未调用 `call_clinic_agent`
- **THEN** companion session 轮次与 `last_suggestion` SHALL 保持不变（相对本请求）

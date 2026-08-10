## MODIFIED Requirements

### Requirement: Intent clinic agent uses bestie clinic_answer generation

`call_clinic_agent` 的最终回答生成 SHALL 使用与 `/clinic/stream` 一致的育儿专家提示词（`clinic_answer`），并纳入 `chat_context`、喂养史、知识与宝宝画像等 clinic 数据准备结果；SHALL NOT 再对 conversation/suggest 使用 `generate_response` 的 history/suggest 旧提示词路径。

#### Scenario: Conversation uses companion persona

- **WHEN** `target_type` 为 conversation 且进入 `call_clinic_agent`
- **THEN** LLM 系统/用户消息 SHALL 按育儿专家模板构建（含可选 chat_context 块，对话非强制点名）

#### Scenario: Suggest also uses companion persona

- **WHEN** `target_type` 为 suggest 且进入 `call_clinic_agent`
- **THEN** 生成 SHALL 同样走专家版 `clinic_answer` 路径（可携带知识/画像），而非旧 suggest_answer 专用路径

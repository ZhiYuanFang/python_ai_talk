## ADDED Requirements

### Requirement: Gate result selects clinic grounding prompt mode
当 clinic（含 intent 共用的 clinic_answer 路径）生成面向用户的回答时，系统 SHALL 根据本轮 `needs_history`（及 `force_needs_history`）选择提示词接地模式：

- `needs_history=true`（或强制需要史）：SHALL 使用要求点名喂养记录依据的提示约束（有记录注入时必须点名）；若注入陪伴对话，SHALL 要求点名对话依据。
- `needs_history=false` 且未强制：SHALL NOT 在系统提示或收尾指令中要求点名喂养记录；SHALL NOT 要求点名近期陪伴对话（口径 B）；SHALL NOT 注入喂养记录明细块；SHALL NOT 注入 `chat_context` 文本块作为「上次你说」类依据；SHALL 在收尾引导家长口语确认是否认这段回应（便于隐式采纳）。

tip 主路径不受本需求改变（仍按 tip 既有有据点名规则）。

#### Scenario: History needed keeps citation rules
- **WHEN** `needs_history` 为 true 且已注入喂养记录
- **THEN** clinic 生成提示词 SHALL 要求点名至少 1 条相关喂养事实

#### Scenario: History not needed drops history and chat citation
- **WHEN** `needs_history` 为 false 且 `force_needs_history` 不为 true
- **THEN** clinic 生成提示词 SHALL NOT 包含「必须点名喂养记录」或「必须点名近期陪伴对话」类硬约束
- **AND** 用户消息 SHALL NOT 包含喂养记录明细块与 `chat_context` 依据块
- **AND** 收尾 SHALL 要求轻轻征求家长对这段回应的肯定/否定

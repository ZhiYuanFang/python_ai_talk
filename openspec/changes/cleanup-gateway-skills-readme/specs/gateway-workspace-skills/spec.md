## ADDED Requirements

### Requirement: Care 卡片推理仅在 Gateway skill

系统 MUST 将 Care Alert 卡片的历史理解与生成置于 OpenClaw `care_alert` workspace skill（或等价 AGENTS 规则）。系统 MUST NOT 在 Python 进程内保留 Care 日分析算力入口或 `generate_care_alerts` 产品路径。出卡权威 MUST 为 `emit_care_cards`（或等价）tool 的结构化 items。

#### Scenario: 无 Python 算卡模块

- **WHEN** 维护者检索 Python 仓 Care 产品路径
- **THEN** MUST NOT 存在可供 Gateway 或 Go 调用的 `/v1/care-alert/analyze` 或进程内日分析编排入口
- **AND** Care workspace skill MUST 指示先只读 history/profile tools，再调用 `emit_care_cards`

#### Scenario: eventId 禁止臆造

- **WHEN** Care skill 生成卡片
- **THEN** eventId MUST 来自 tool 返回的历史或事件对照
- **AND** MUST NOT 编造通识知识库依据作为卡片权威

### Requirement: Intent workspace 适配 tool-calling

系统 MUST 在 `intent` workspace 提供面向 OpenClaw 的操作规则：低置信只追问不写库；写史仅经 history_* tools；成功后可选飞轮 tool；对用户仅 NL。系统 MUST NOT 将旧 LangGraph「整段 JSON 意图信封」作为 Gateway 最终契约照搬进 skill。

#### Scenario: 提炼原则而非照搬 classify prompt

- **WHEN** 从旧 `intent_classification` 迁规则
- **THEN** skill MUST 保留事件 id 不编造、叶子可写、读史 top_k/忽略时间窗等有效原则
- **AND** MUST NOT 要求模型只输出 `target_type`/`events[]`/`need_confirm` JSON 作为产品响应

#### Scenario: 事件表经 tool 获取

- **WHEN** Intent agent 需要事件字典或历史
- **THEN** MUST 优先调用已注册的 history_options / history_filter 等 tools
- **AND** MUST NOT 把全量事件树默认注入 bootstrap 大段文本作为唯一手段

### Requirement: Clinic workspace 只读 + 隐式采纳 tool

系统 MUST 为 `clinic` workspace 提供只读 history/知识与隐式采纳相关 tool 指引。Clinic/Care MUST NOT 被 allow 写史 tools。

#### Scenario: Clinic ACL

- **WHEN** 配置 `agents.entries.clinic.tools.allow`
- **THEN** MUST NOT 包含 `history_create` / `history_update` / `history_delete` / `history_end_latest`
- **AND** MAY 包含 `clinic_judge_implicit_acceptance` 与 `flywheel_clinic_record`

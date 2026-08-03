## ADDED Requirements

### Requirement: Judge needs history before scope and fetch

系统在判定喂养历史的事件类型与时间范围之前，SHALL 先执行独立节点判断是否需要根据喂养历史回答；SHALL NOT 将 `needs_history` 并入 `data_requirement` 的职责。

#### Scenario: Clinic open chat runs gate first

- **WHEN** `/v1/clinic/stream` 或 intent 的 conversation/suggest 路径进入 clinic 数据准备
- **THEN** 系统 SHALL 先运行 `judge_needs_history`，再根据结果决定是否运行 `judge_data_requirement` 与 `fetch_history`

#### Scenario: Scope node remains scope-only

- **WHEN** `needs_history` 为 true 且执行 `judge_data_requirement`
- **THEN** 该节点 SHALL 仅产出 event_ids / time_range / limit（及既有自定义时间字段），SHALL NOT 负责是否需要历史的布尔判定

### Requirement: Loose gate with fail-open default

`judge_needs_history` SHALL 采用宽松策略：若喂养历史可能有助于回答则判定为需要；LLM 调用失败、解析失败或缺少明确布尔时 SHALL 默认 `needs_history=true`。

#### Scenario: Ambiguous feeding-related advice

- **WHEN** 用户问题与宝宝近期喂养/睡眠等模式相关，即使未明确「查记录」
- **THEN** 门禁 SHALL 倾向 `needs_history=true`

#### Scenario: Pure chit-chat or generic knowledge

- **WHEN** 用户问题为纯闲聊或与该宝宝近期记录无关的通用知识
- **THEN** 门禁 MAY 判定 `needs_history=false`

#### Scenario: LLM or parse failure

- **WHEN** 门禁 LLM 失败或无法解析出合法布尔
- **THEN** 系统 SHALL 将 `needs_history` 设为 true

### Requirement: Skip scope and fetch when history not needed

当 `needs_history` 为 false 且未被上游强制时，系统 SHALL 跳过 `judge_data_requirement` 与 `fetch_history`，并将 `history_events` 置为空列表；SHALL NOT 因此跳过 `search_vectors` 或 `fetch_baby_profile`（除非既有其它旗标如 `skip_knowledge` 另有规定）。

#### Scenario: Gate says false

- **WHEN** `needs_history` 为 false 且 `force_needs_history` 不为 true
- **THEN** 系统 SHALL 不调用范围判断 LLM，SHALL 不请求喂养历史 HTTP API，且 `history_events` SHALL 为空列表
- **AND** 数据准备 SHALL 继续执行知识检索与宝宝画像（在适用路径上）

#### Scenario: Thinking copy matches executed nodes

- **WHEN** `needs_history` 为 false 从而跳过拉取
- **THEN** 流式 thinking SHALL NOT 展示「正在拉取/翻看喂养记录」类仅属于 `fetch_history` 的文案

### Requirement: Upstream force needs history

intent 的 `target_type=history` 与 tip 主路径 SHALL 强制需要喂养历史：SHALL 跳过 `judge_needs_history`，或设置 `force_needs_history=true` 使得范围判断与拉取仍执行。

#### Scenario: Intent history path

- **WHEN** `call_clinic_agent` 处理 `target_type=history`
- **THEN** 系统 SHALL 不因门禁而跳过历史拉取，SHALL 仍按既有逻辑拉取喂养历史（并可继续 `skip_knowledge`）

#### Scenario: Tip stream path

- **WHEN** tip 流式数据准备运行
- **THEN** 系统 SHALL 不运行 `judge_needs_history`，SHALL 继续使用既有硬编码或等价的 `data_requirement` 拉取历史

### Requirement: Gate only affects feeding history

本能力 SHALL 仅门禁喂养历史数据准备；SHALL NOT 改变知识向量检索或宝宝画像的触发条件（`skip_knowledge` 等既有行为除外）。

#### Scenario: Vectors and profile unchanged by gate false

- **WHEN** clinic 续聊路径上 `needs_history` 为 false
- **THEN** 系统 SHALL 仍可执行 `search_vectors` 与 `fetch_baby_profile`（除非该路径另有跳过规则）

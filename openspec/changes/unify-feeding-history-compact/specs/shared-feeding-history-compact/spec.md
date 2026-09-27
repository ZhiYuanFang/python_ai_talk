## ADDED Requirements

### Requirement: Shared compact history builder lives in app/shared

系统 SHALL 在 `app/shared` 提供唯一的喂养史紧凑聚合构建函数，将原始 `history_events` 转为按上海日历日 × 事件名聚合的文本行，并可选产出 `eventName=eventId` 对照表（legend）。行内 MUST NOT 嵌入 eventId。聚合规则本变更 MUST 与迁入前 care_alert compact 行为一致（日历日标签、时刻列表、按类型总量/时长/次数分段）。

#### Scenario: Build returns text and legend

- **WHEN** 调用方传入含可解析时间与事件名的 history_events
- **THEN** 函数返回非空的 history 文本块（多行聚合）以及可用的 name→id legend（当事件带 id 时）
- **AND** history 文本行中 MUST NOT 出现 eventId

#### Scenario: Empty input

- **WHEN** history_events 为空或无法解析出任何日历日
- **THEN** history 文本 SHALL 表示为无数据占位（如「（无）」）
- **AND** legend MAY 为空串

### Requirement: Care-alert consumes shared compact with legend

护理留意分析提示词 SHALL 使用共享构建函数注入近期喂养聚合文本，并 SHALL 注入 legend 供模型回填 `eventId`。软兜底与规范化路径 MUST 继续依赖合法 eventId（无 legend 时允许空 items，行为与迁入前一致）。拉取时间窗与 limit MUST 仍由 care_alert 自身 DataRequirement 决定（本变更不改为统一窗长）。

#### Scenario: Analyze user message includes history and legend

- **WHEN** care_alert 组装 analyze 用户消息且存在可用历史
- **THEN** 消息包含共享聚合史块
- **AND** 包含独立的事件名与 id 对照说明（仅回填用）

### Requirement: Growth-trajectory generate uses shared compact text

成长轨迹最终生成用户消息 SHALL 使用共享聚合的 `history_text` 作为近期喂养背景，SHALL NOT 再注入原始 history 事件 JSON 预览作为主史块。`prior_feedback`、问答与画像注入 MUST NOT 因本需求改变。legend MUST NOT 作为成长轨迹必选注入。拉取窗长 MUST 仍由成长轨迹自身 DataRequirement 决定。

#### Scenario: Generate prompt uses compact not raw JSON list

- **WHEN** growth_trajectory 进入 generate 且 state 含 history_events
- **THEN** 用户消息喂养段为共享聚合文本（可空则弱化喂养段）
- **AND** MUST NOT 以未聚合的事件对象 JSON 数组作为该段主内容

### Requirement: Clinic needs-history path uses shared compact text

当 clinic 以需要喂养史模式生成回答时，注入 LLM 的喂养史主块 SHALL 为共享紧凑聚合文本。系统 MUST NOT 再调用 `build_daily_history_summary`。clinic 的历史拉取范围仍由既有 needs_history / data_requirement 逻辑决定。

#### Scenario: Clinic with history injects compact block

- **WHEN** clinic 构建回答用户消息且 needs_history 为真且存在 history_events
- **THEN** 用户消息包含共享聚合史块
- **AND** MUST NOT 包含由 `build_daily_history_summary` 生成的薄按日汇总段

### Requirement: Intent daily mode uses shared compact text without legend

当意图查记录走 `history_mode=daily` 模板播报时，播报 content SHALL 使用共享聚合的 `history_text`（无数据时给出无记录类说明）。播报 MUST NOT 向用户输出 legend（name=id）对照表。`history_mode=point`（及父事件塌缩点查）路径 MUST NOT 因本需求改写。

#### Scenario: Daily mode speaks compact lines

- **WHEN** speak_history 处理 read 且 history_mode 为 daily 且拉史返回若干行
- **THEN** content 基于共享聚合文本
- **AND** content MUST NOT 含「事件名=数字id」对照表行

#### Scenario: Point mode unchanged

- **WHEN** speak_history 处理 read 且 history_mode 为 point（或缺省 point）
- **THEN** 仍使用既有点查模板播报
- **AND** MUST NOT 强制改为紧凑聚合行

### Requirement: Thin daily summary helper is removed

系统 MUST NOT 再提供或调用 `build_daily_history_summary`。原依赖方 MUST 已改用共享紧凑聚合。

#### Scenario: No remaining callers

- **WHEN** 本变更落地后检查代码库
- **THEN** 不存在 `build_daily_history_summary` 定义与引用

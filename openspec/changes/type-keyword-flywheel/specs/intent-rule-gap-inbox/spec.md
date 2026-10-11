## MODIFIED Requirements

### Requirement: 非事件维规则缺口须落库
当且仅当 **时间** 或 **数量** 维出现「规则未覆盖且调用对应小 LLM 并得到可记录结果」时，系统 SHALL 将缺口记录持久化到 Python 侧收件箱（非向量库）。记录 MUST 至少包含：`dimension`（`time`|`quantity`）、`segment_text`、`utterance`、`reason`、`created_at`、`llm_used=true`；MAY 含 `llm_result` 摘要、`device_no`、`status`。系统 MUST NOT 因 TYPE/SHAPE/EVENT 维 LLM 或类型飞轮写入缺口。系统 MUST NOT 将 number 缺量追问（无量线索）作为 Hub 默认展示的规则缺口主来源。

#### Scenario: 时间规则 miss 且 LLM 捕捉
- **WHEN** 时间维规则半命中或抽空后调用 TIME 小 LLM
- **THEN** 系统 SHALL 写入一条 `dimension=time` 且 `llm_used=true` 的缺口记录

#### Scenario: TYPE 兜底不进缺口
- **WHEN** TYPE 小 LLM 被调用或类型关键字写入飞轮
- **THEN** 系统 SHALL NOT 写入 `dimension=type` 的规则缺口

### Requirement: Python admin 列表与标已处理
系统 SHALL 提供管理端 HTTP API（如 `/v1/admin/rule-gaps`）支持分页列表（默认新→旧）、按维度/状态筛选，以及将记录标为已处理（`dismissed`）或删除。**默认列表（未指定 dimension 时）MUST 仅包含 `time` 与 `quantity`。** 鉴权依赖内网调用，与意图缓存 admin 同级。

#### Scenario: 默认列表只有 TIME/QTY
- **WHEN** 管理端 GET 缺口列表且未传 dimension 过滤
- **THEN** 响应 items 的 dimension SHALL 仅能为 time 或 quantity
- **AND** SHALL NOT 包含 type、shape、event

#### Scenario: 标已处理
- **WHEN** 管理端将某条 status 更新为 dismissed
- **THEN** 后续默认 open 列表 SHALL NOT 再展示该条（除非筛选包含 dismissed）

## REMOVED Requirements

### Requirement: 事件维 miss 可记入缺口
**Reason**：事件种子由短说法向量库与 Hub 事件向量管理整理；缺口箱只服务 TIME/QTY 规则扩展。
**Migration**：停止 `dimension=event` 的 `rule_gap` 写入；人工补种子走 `/admin/intent-cache`。

## ADDED Requirements

### Requirement: 缺口不得写入类型或事件飞轮
缺口收件箱 MUST NOT 自动生成或热更新代码规则；MUST NOT 因缺口记录而写入事件短说法库或类型关键字库。TIME/QTY 规则整理由人工改代码发版完成；TYPE/EVENT 飞轮由运行时关键字写入与 Hub 向量页整理。

#### Scenario: 时间缺口不写类型库
- **WHEN** 一条 time 维缺口被落库
- **THEN** 系统 SHALL NOT 因此向类型关键字集合或 `feeding_intents` 新增 document

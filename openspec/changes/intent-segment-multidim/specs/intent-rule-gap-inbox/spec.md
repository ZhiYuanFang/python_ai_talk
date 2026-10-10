## ADDED Requirements

### Requirement: 非事件维规则缺口须落库
当类型、时间、数量或形态维出现规则未覆盖（含时间半命中、类型冲突/无线索而调用 LLM 兜底、数量规则 miss 后 LLM 兜底、number 叶缺量触发追问等）时，系统 SHALL 将缺口记录持久化到 Python 侧收件箱（非向量库）。记录 MUST 至少包含：`dimension`、`segment_text`、`utterance`、`reason`、`created_at`；MAY 含 `llm_used`、`llm_result` 摘要、`device_no`、`status`。

#### Scenario: 时间半命中写入缺口
- **WHEN** 时间维规则抽到钟点但仍有未消费日/段残留（半命中）
- **THEN** 系统 SHALL 写入一条 `dimension` 为时间类的缺口记录，含段原文与整句

### Requirement: 事件维 miss 可记入缺口
当事件维词典与向量均未命中而进入事件小 LLM 或导致段失败时，系统 SHALL 写入 `dimension=event`（或等价）的缺口记录，便于人工补短说法种子。

#### Scenario: 事件向量未过门槛
- **WHEN** 事件维 Top-1 score &lt; 0.72 且最终未得到稳定 event_id
- **THEN** 系统 SHALL 落一条事件维缺口记录

### Requirement: 短窗去重
系统 SHALL 对相同 `dimension` + 规范化 `segment_text` 在短时间窗内去重，避免重复刷屏。

#### Scenario: 连发同一缺口
- **WHEN** 同一设备短窗内多次触发相同维度与相同段原文缺口
- **THEN** 系统 SHALL NOT 为每一次都新增独立 open 记录（更新计数或跳过均可）

### Requirement: Python admin 列表与标已处理
系统 SHALL 提供管理端 HTTP API（如 `/v1/admin/rule-gaps`）支持分页列表（默认新→旧）、按维度/状态筛选，以及将记录标为已处理（`dismissed`）或删除。鉴权依赖内网调用，与意图缓存 admin 同级。

#### Scenario: 列表缺口
- **WHEN** 管理端 GET 缺口列表
- **THEN** 响应 SHALL 含 items 与分页信息，items 按时间新→旧

#### Scenario: 标已处理
- **WHEN** 管理端将某条 status 更新为 dismissed
- **THEN** 后续默认 open 列表 SHALL NOT 再展示该条（除非筛选包含 dismissed）

### Requirement: 缺口不得自动改规则或写事件飞轮
缺口收件箱 MUST NOT 自动生成或热更新代码规则；MUST NOT 因缺口记录而写入事件短说法向量库。整理规则由人工改代码发版完成。

#### Scenario: 写入缺口不改向量库
- **WHEN** 一条时间维缺口被落库
- **THEN** 系统 SHALL NOT 因此向 `feeding_intents` 事件说法库新增 document

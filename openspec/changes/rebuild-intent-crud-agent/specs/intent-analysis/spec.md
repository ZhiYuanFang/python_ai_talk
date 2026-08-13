## MODIFIED Requirements

### Requirement: 意图分析接口
系统 SHALL 提供 `/v1/analyze/intent` HTTP POST 接口，接收自然语言文本和设备编号，返回结构化意图分析结果。该非流式端点 SHALL 与 `/v1/analyze/intent/stream` 使用同一套意图图与后处理（pending、意图缓存、分类、Python 历史 CRUD、查记录生成 `content`）。系统 SHALL NOT 在该非流式端点调用 clinic agent 或 `clinic_graph`。响应 MUST 为 `IntentResponse`（含 `content`；CRUD 时含 `op` 与 `events`）。

#### Scenario: 成功识别喂养开始意图
- **WHEN** 客户端发送 POST 请求到 `/v1/analyze/intent`，body 包含有效 `text`「开始喂奶」与 `device_no`
- **THEN** 服务返回 HTTP 200
- **AND** 响应 `target_type` 为 `feeding`（或 `op=create` 且动作为 `start`）
- **AND** `content` 为 Python 执行后的已记录类文案或确认话术（若 `need_confirm`）

#### Scenario: 成功识别单次喂养记录意图
- **WHEN** 客户端发送 POST 请求到 `/v1/analyze/intent`，body 的 `text` 为「刚才喝了120ml奶粉」
- **THEN** 服务返回 HTTP 200
- **AND** 不得仅因非流式而改写为 `conversation`/`reply` 陪伴回答

#### Scenario: 成功识别历史查询意图
- **WHEN** 客户端发送 POST 请求到 `/v1/analyze/intent`，body 的 `text` 为「今天吃了多少」
- **THEN** 服务返回 HTTP 200
- **AND** `op` 为 `read` 或 `target_type` 为 `history`
- **AND** `content` 为基于历史数据的自然语言（无记录时明确说明）

#### Scenario: 非 CRUD 闲聊
- **WHEN** 客户端发送 POST 请求到 `/v1/analyze/intent`，body 的 `text` 为「你好」
- **THEN** 服务返回 HTTP 200
- **AND** `target_type` 为 `conversation`
- **AND** SHALL NOT 调用 `clinic_graph`

#### Scenario: 失败 - 缺少必要参数
- **WHEN** 客户端发送 POST 请求到 `/v1/analyze/intent`，body 缺少 `text` 或 `device_no` 字段
- **THEN** 服务返回 HTTP 4xx，响应 body 包含错误信息

### Requirement: 意图分析接口实现方式
意图分析接口 `/v1/analyze/intent` SHALL 使用 LangGraph `intent_graph` 编排（与 stream 冷启动同源）。SHALL NOT 直接调用 clinic agent。history 后处理 SHALL 在意图图内拉史并生成 `content`。suggest 成长建议 SHALL NOT 再作为本接口的后处理分支（改走 `/v1/clinic`）。

#### Scenario: 使用 LangGraph 编排
- **WHEN** 接收到非流式意图分析请求
- **THEN** 系统 SHALL 调用 `intent_graph` 执行意图分析流程
- **AND** SHALL NOT 使用 `call_clinic_agent` 完成本请求

#### Scenario: history 意图后处理
- **WHEN** 用户输入「今天喝了多少奶粉」，意图为查记录
- **THEN** 系统 SHALL 在意图图内拉取对应历史
- **AND** 将自然语言回答填入 `IntentResponse.content`
- **AND** SHALL NOT 调用 `clinic_graph`

#### Scenario: feeding 由 Python 执行落库
- **WHEN** 意图为喂养 create/update/delete 且无需继续确认
- **THEN** 系统 SHALL 在 Python 侧调用 history HTTP 后返回 `IntentResponse`
- **AND** SHALL NOT 把未执行的结构交给 Go 再判断写库

#### Scenario: conversation 不进 clinic
- **WHEN** 意图为 `conversation`
- **THEN** 系统 SHALL 返回分类或短回复 `content`
- **AND** SHALL NOT 调用 clinic agent

### Requirement: 系统分析用户输入的意图
系统 SHALL 分析用户输入，识别事件增删改查（含多事件）或非 CRUD 闲聊/退出，并支持流式与非流式返回。系统 SHALL NOT 在意图路径内部调用 clinic agent 获取陪伴长文。系统 MUST NOT 将字典外专名当作新事件类型创建；查记录中的字典外专名 SHALL 按已有事件备注处理。

#### Scenario: 多事件增
- **WHEN** 用户输入「没吃，睡着了」且分类为多事件 create
- **THEN** 响应 SHALL 带 `events` 列表（或确认话术列出多件）
- **AND** 高置信单事件向量 MUST NOT 单独结束为本请求唯一结果

#### Scenario: 流式请求暴露节点进度
- **WHEN** 客户端请求 `/v1/analyze/intent/stream`
- **THEN** 系统在节点执行时发送 thinking 事件
- **AND** 最终 answer 与非流式 JSON 字段语义一致

#### Scenario: 非流式请求与流式同图
- **WHEN** 客户端请求非流式 `/v1/analyze/intent`
- **THEN** 系统返回 JSON 格式结果
- **AND** 内部 SHALL 走与 stream 相同的意图图，SHALL NOT 调用 clinic agent

#### Scenario: 字典外 AD 不建新事件
- **WHEN** 用户输入「上一次什么时候吃的 AD」
- **THEN** 系统 SHALL NOT 创建名为 AD 的事件类型
- **AND** SHALL 走查记录确认（候选为字典中的营养品等）或说明无法确定事件

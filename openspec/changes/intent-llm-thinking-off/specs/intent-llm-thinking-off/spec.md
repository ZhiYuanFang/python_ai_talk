## ADDED Requirements

### Requirement: 意图链路关闭模型思考

喂养意图链路上的每一次 LLM 调用 MUST 使用 `llm_client.stream(thinking_enabled=False)`。provider 为 `aliyun_dashscope` 时，该请求 MUST 带 `enable_thinking: false`。诊所回答、诊所翻记录判定、成长轨迹、留意点的 LLM MUST 继续 `thinking_enabled=True` 并透出模型 reasoning。

#### Scenario: 意图分类不再生成思考

- **WHEN** 意图流式请求进入分类、切段、维度判定、备注、事件反查、播报策略、预测回答、澄清、漏答或日汇总的 LLM
- **THEN** 该次请求的 `thinking_enabled` MUST 为 false
- **THEN** 当前型号为通义千问时，请求 MUST 包含 `enable_thinking: false`

#### Scenario: 诊所回答仍开启思考

- **WHEN** 诊所流式回答调用 `stream_response`
- **THEN** 该次请求 MUST 仍为 `thinking_enabled=True`
- **THEN** 模型 reasoning MUST 仍按现有路径推到 thinking 事件

### Requirement: 意图等待期间轮换固定思考字幕

`thinking_enabled=False` 的 `stream_llm_collect` 从调用开始到该次调用结束，MUST 向外推送 thinking。第一条 MUST 在调用开始时立即发出，内容为 `\r努力思考中`。此后 MUST 每 1 秒在 `\r努力思考中` 与 `\r正在思考中` 之间切换。`\r` 后 MUST NOT 另加空格。模型 reasoning 文本 MUST NOT 出现在这些 thinking 事件里。调用结束（含失败返回）后 MUST 停止轮换。图节点经 `emit_thinking` 发出的固定编排字幕 MUST 保持原有文案。

#### Scenario: 调用一开始就显示第一句

- **WHEN** 意图链路的一次 LLM 调用刚开始、模型尚未返回正文
- **THEN** 客户端 MUST 收到 content 为 `\r努力思考中` 的 thinking 事件

#### Scenario: 超过一秒后换成另一句

- **WHEN** 同一次调用持续超过 1 秒
- **THEN** 下一条 thinking 的 content MUST 为 `\r正在思考中`
- **THEN** 再过 1 秒 MUST 回到 `\r努力思考中`

#### Scenario: 调用结束即停

- **WHEN** 该次 `stream_llm_collect` 返回或失败退出
- **THEN** MUST NOT 再推送新的轮换句

#### Scenario: 编排字幕文案不变

- **WHEN** 图节点在 LLM 之前推送「正在分析你的意图」一类固定字幕
- **THEN** 该条 content MUST 仍是原来的编排文案

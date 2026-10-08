## ADDED Requirements

### Requirement: Orchestration caption then LLM reasoning for LLM nodes

对于对外 SSE 路径上含 LLM 调用的编排节点，系统 SHALL 先推送该节点的编排字幕（`emit_thinking` 或等价），再在 LLM 流式过程中推送模型 reasoning 增量。编排字幕与 reasoning 增量均使用 `type=thinking`，但语义上字幕表示「节点开始」，reasoning 表示「模型思考」。SHALL NOT 仅以编排字幕替代模型 reasoning。

#### Scenario: Caption precedes classify reasoning

- **WHEN** intent 流式执行 `classify_intent`
- **THEN** 客户端 SHALL 先收到该节点编排字幕类 thinking，再（若模型有 reasoning）收到 reasoning 增量

#### Scenario: Caption precedes clinic gate reasoning

- **WHEN** clinic 流式执行 `judge_needs_history` 且调用 LLM
- **THEN** 客户端 SHALL 先收到门禁节点编排字幕，再收到该次 LLM 的 reasoning 增量（若有）

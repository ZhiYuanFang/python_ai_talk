## Why

当前 intent 接口（`/v1/analyze/intent`）仅支持非流式返回，无法将 LangGraph 的编排过程（节点思考进度）暴露给前端。而 clinic 接口已支持流式 SSE 返回，包含 thinking 事件。为了统一用户体验，intent 接口需要增加 stream 参数支持流式返回。

同时，当意图识别为"喂养建议"时，intent 流程内部需要调用 clinic agent 获取回答，避免前端发起二次请求。

此外，之前新增的 `/v1/analyze/intent/confirm` 接口需要确认 go_ai_talk 和 flutter_ai_talk 是否需要适配修改。

## What Changes

- **intent 接口增加 stream 参数**：默认 false（非流式），true 时通过 SSE 返回 thinking 事件和最终结果
- **intent 流式响应暴露节点思考进度**：类似 clinic 的 thinking 事件，暴露向量匹配、LLM 分类、确认等节点的执行进度
- **intent 喂养建议节点调用 clinic agent**：当意图为 conversation/suggest 时，内部调用 clinic graph 获取回答，避免前端二次请求
- **confirm 接口适配分析**：调研 go_ai_talk 和 flutter_ai_talk 是否需要修改以适配新的确认流程

## Capabilities

### New Capabilities

- `intent-stream-response`: intent 接口流式响应能力，通过 SSE 暴露节点思考进度

### Modified Capabilities

- `intent-analysis`: 意图分析能力，新增 stream 参数和 clinic agent 内部调用
- `feeding-intent-user-confirmation`: 用户确认机制，需要适配 go_ai_talk 和 flutter_ai_talk

## Impact

- **API 接口**：`/v1/analyze/intent` 新增 stream 参数，新增 `/v1/analyze/intent/stream` 流式端点
- **意图图**：intent_graph 新增 clinic agent 调用节点
- **兄弟仓**：go_ai_talk 和 flutter_ai_talk 可能需要适配 confirm 接口
- **前端**：需要处理 intent 流式 SSE 响应

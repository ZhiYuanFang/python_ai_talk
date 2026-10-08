## Why

前端需要在所有流式智能体上实时展示模型原生 reasoning，但当前仅 clinic 主回答、care-alert 生成、growth 轨迹 LLM 走 `stream(thinking_enabled=True)` 并透出；intent 分类、intent pending 澄清、clinic 门禁判定（`judge_needs_history` / `judge_data_requirement`）仍用 `invoke` 黑盒，SSE 只有编排字幕。产品已确认策略 B：对外 SSE 路径上每一次 LLM 都必须逐字透出 reasoning。

## What Changes

- **BREAKING（工程约定）**：废止「图内部判定节点允许 `invoke`」对对外 SSE 路径的豁免；SSE 路径上的 LLM（含意图分类、门禁判定、pending 澄清）MUST 使用 `llm_client.stream(thinking_enabled=True)`，并将 reasoning 增量以 `type=thinking` SSE 透出。
- 抽取/统一共享「流式收集 + 透 reasoning」辅助（对齐 growth 既有模式），图内节点经 `emit_llm_thinking_delta`；图外 pending 由 intent stream 路由注入回调透出。
- 改造缺口：`classify_intent`、`judge_needs_history`、`judge_data_requirement`、`llm_resolve_pending_reply` + `/intent/stream` pending 分支。
- 审计已齐路径（clinic 主回答、care-alert、growth）：确认无回归；不改 SSE 事件类型契约。
- 同步更新 `openspec/project.md` §1.0 流式约定文案。
- 同步非 SSE 接口可继续 `invoke`；无 LLM 短路（缓存命中、精确父名、模板播报）不强制伪 thinking。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `llm-native-stream-thinking`：将「原生 thinking 透出」从主回答扩展为对外 SSE 路径上的全部 LLM 调用；明确多段 reasoning 气泡合法；同步路径仍可不透 SSE。
- `intent-stream-response`：冷启动 `classify_intent` 与 pending 澄清路径 MUST 透出 LLM reasoning；pending 不得仅返回 answer 而无 thinking 通道。
- `progressive-stream-thinking`：补充判定/分类类 LLM 节点在编排字幕之后仍须透出模型 reasoning 增量（与字幕区分）。

## Impact

- 代码：`app/shared/graphs/`（helper + judge 节点）、`app/feeding/graphs/nodes/classify_intent.py`、`app/feeding/services/clarification.py`、`app/api/routes/intent.py`；可能微调 growth helper 改为调用 shared；`openspec/project.md`。
- API：SSE 仍为 `thinking` / `answer` / `done`；客户端按既有段首 `\r` 开泡约定即可，**不要求**为透出本身改 Go 契约（若 Go 未代理 intent stream 或丢弃 thinking，属调用侧问题）。
- 体验：clinic 单次请求可出现多段 reasoning（门禁 ×2 + 主回答）；费用与延迟上升为已知取舍。
- 禁止新增测试文件。

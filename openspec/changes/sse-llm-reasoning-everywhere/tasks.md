## 1. 工程约定与共享 helper

- [x] 1.1 更新 `openspec/project.md` §1.0：对外 SSE 路径上的 LLM（含判定/分类）MUST `stream(thinking_enabled=True)` 并透出 reasoning；删除「判定节点允许 invoke」对 SSE 的豁免；同步非 SSE 仍可 invoke
- [x] 1.2 在 `app/shared/` 新增流式收集 helper（对齐 growth）：`stream` + `thinking_enabled=True`，thinking 走 `emit_llm_thinking_delta` 或可选 `on_thinking` 回调，聚合返回 content；中文注释完整
- [x] 1.3（可选薄封装）让 growth `question_utils._stream_llm_collect` 复用 shared helper，行为不变

## 2. 图内判定与分类缺口

- [x] 2.1 改造 `judge_needs_history`：SSE/统一路径用 shared helper 替代 `invoke`，透出 reasoning；解析逻辑不变
- [x] 2.2 改造 `judge_data_requirement`：同上
- [x] 2.3 改造 `classify_intent`：用 shared helper 替代 `invoke`，透出 reasoning；聚合 content 后再解析 `intent_result`，不把 JSON 片段当 answer SSE

## 3. Intent pending 流式透出

- [x] 3.1 扩展 `llm_resolve_pending_reply`（或等价）：支持可选 `on_thinking`；内部 `stream`+`thinking_enabled=True`；无回调时不破坏非流调用方
- [x] 3.2 改造 `/v1/analyze/intent/stream` pending 分支：澄清过程中 yield `thinking` 增量，再 yield `answer`/`[DONE]`；禁止仅 invoke 后一条 answer
- [x] 3.3 确认非流 `/v1/analyze/intent` pending 仍同步返回完整 JSON

## 4. 已齐路径审计

- [x] 4.1 审计 clinic `stream_response` + 路由：主回答 reasoning 透出与段首 `\r` 约定仍正确
- [x] 4.2 审计 care-alert `generate_care_alerts`：已 `stream`+`emit_llm_thinking_delta`，无回归
- [x] 4.3 审计 growth 轨迹 LLM 节点：与 shared helper 一致或仍透 reasoning

## 5. 手工验收（无测试文件）

- [x] 5.1 clinic/stream：可见门禁字幕 → 门禁 reasoning（若有）→ 主回答字幕/reasoning → answer
- [x] 5.2 intent/stream 冷启动：classify 字幕 → classify reasoning → answer
- [x] 5.3 intent/stream pending：澄清 reasoning → answer
- [x] 5.4 care-alert stream 与 growth turn：reasoning 仍可见
- [x] 5.5 非流 intent/clinic：仍返回完整 JSON，无 SSE 要求

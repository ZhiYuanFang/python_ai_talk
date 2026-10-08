## Context

四条对外 SSE 入口：clinic `/stream`、intent `/intent/stream`、care-alert `/analyze/stream`、growth-trajectory turn。

现状分层：

- **编排字幕**（`emit_thinking` + 段首 `\r`）：intent/clinic 流式已有。
- **模型 reasoning**（`llm_client.stream(thinking_enabled=True)` → `LLMResponse.thinking` → SSE `thinking`）：clinic 主回答、care-alert 生成、growth `_stream_llm_collect` 已齐；intent `classify_intent`、pending `llm_resolve_pending_reply`、shared `judge_needs_history` / `judge_data_requirement` 仍为 `invoke`。
- `openspec/project.md` §1.0 明文允许「判定节点 invoke」，与产品策略 B 冲突。

基础设施已存在：`emit_llm_thinking_delta`、`ensure_orchestration_thinking_content`、clinic 路由对「本流首次 LLM thinking」加段首 `\r`。

## Goals / Non-Goals

**Goals:**

- 对外 SSE 路径上每一次 LLM 调用均真流式，并逐字透出 reasoning。
- 图内统一走 shared helper + `emit_llm_thinking_delta`；图外 pending 由 intent stream 路由透出。
- 更新 `project.md` 约定；规格覆盖多段气泡与 pending 缺口。
- 同步非 SSE、无 LLM 短路行为保持可理解且不伪造成流。

**Non-Goals:**

- 不改 SSE 事件类型字段（仍 thinking / answer / done）。
- 不为透出本身改 Go API 契约；不新建 tip 产品线。
- 不强制非 SSE 同步接口改 stream（可继续 invoke）。
- 不新增测试文件；不做「关闭 reasoning」运行时开关（除非后续另开 change）。
- 不把半截 JSON answer 推给前端（分类/判定仍聚合 content 再解析）。

## Decisions

### D1：策略 B（SSE 路径全覆盖）

凡在对外 SSE 请求处理链上调用的 LLM（含门禁与分类），MUST `stream` + `thinking_enabled=True` 并透出 reasoning。  
**替代**：仅主 LLM（策略 A）——已否决，产品要全覆盖。

### D2：共享 `stream_llm_collect`（从 growth 对齐）

在 `app/shared/` 提供异步 helper：

- 入参：messages、model_config、system_prompt、`node_name`、可选 `on_thinking` 回调。
- 行为：`llm_client.stream(..., thinking_enabled=True)`；有 thinking 时优先 `on_thinking`，否则 `emit_llm_thinking_delta(node_name, …)`；聚合并返回 answer `content`。
- growth 可改为调用该 helper（或薄包装），避免三套复制。

**替代**：各模块各自 stream——易漂移；否决。

### D3：图内 vs 图外透出通道

| 场景 | 通道 |
|------|------|
| 图节点（classify、judges、care/growth） | `emit_llm_thinking_delta` → `astream(custom)` → 路由转 SSE |
| intent pending（图外） | `on_thinking` → 路由直接 `yield` thinking SSE |
| clinic 主回答（路由层迭代） | 保持现有路由对 `chunk.thinking` 的处理 |

`ainvoke` / 无 writer 时 emit 静默跳过；节点实现可统一走 stream helper，同步路径不强制 SSE。

### D4：pending 流式改造

`/intent/stream` 命中 pending 时，不得再「先 invoke 完再一条 answer」。改为：可选编排字幕 → stream 澄清 LLM（透 reasoning）→ 再 answer / DONE。  
`try_handle_pending` / `llm_resolve_pending_reply` 需支持流式回调或拆出「可观察」解析路径，避免破坏非流 `/intent`。

### D5：多段气泡为预期行为

clinic：字幕₁ → 门禁 reasoning → 字幕₂ → 范围 reasoning → 字幕₃ → 主回答 reasoning → answer tokens。  
段首 `\r` 规则不变：编排字幕与「本流/本段首次 LLM thinking」开泡；后续 LLM 增量不加 `\r`。

### D6：`project.md` 文案

改为：对外 SSE 路径上的 LLM（含判定/分类）MUST stream + 透 reasoning；同步非 SSE 仍可 invoke。删除「判定节点允许 invoke」对 SSE 的豁免表述。

## Risks / Trade-offs

- **[延迟/费用]** 门禁与分类开启原生 thinking → Mitigation：接受为产品取舍；不在本 change 做降级开关。
- **[UI 嘈杂]** 多段 reasoning → Mitigation：规格写明合法；前端已按段首 `\r` 分泡。
- **[pending API 形状]** 澄清函数签名扩展 → Mitigation：可选 `on_thinking`；非流路径不传回调，行为等价。
- **[半截 JSON]** 若误把分类 content 当 answer SSE → Mitigation：仅透 thinking；content 聚合后再解析。
- **[Go 未走 stream]** 前端仍无思考 → Mitigation：本 change 不改 Go；文档/验收注明须打 stream 端点。

## Migration Plan

1. 落地 shared helper → 改缺口节点 → 改 intent pending 流式路由 → 更新 `project.md`。
2. 手工验收：四条 SSE 入口各走一遍，确认 reasoning 增量可见；非流 intent/clinic 仍返回完整 JSON。
3. 回滚：恢复 invoke 调用点即可；无数据迁移。

## Open Questions

（无阻塞项；实现时若 pending 拆分方式与现有 `ResolveResult` 冲突，优先「回调透 thinking + 同步返回 ResolveResult」最小改动。）

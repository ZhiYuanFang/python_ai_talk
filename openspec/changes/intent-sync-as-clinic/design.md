## Context

非流式 `/v1/analyze/intent` 历史上跑完整意图图（喂养落库 + 部分类型转 clinic）。产品与前端已将其当作陪伴入口；流式 `/intent/stream` 仍保留意图图。路径因前端绑定不可迁到 `/clinic`。

## Goals / Non-Goals

**Goals:**

- `analyze_intent` 仅调用 `call_clinic_agent`，组装 `IntentResponse` 返回。
- 读/写 companion session、clinic_graph 数据准备与同步生成行为与现有 `call_clinic_agent` 一致。
- 保持 URL 与 `IntentRequest`/`IntentResponse` 外壳。

**Non-Goals:**

- 不改 `/intent/stream`。
- 不删除 intent_graph / pending / 喂养管道（流式仍用）。
- 不把路由文件挪到 clinic 模块（仅行为对齐 clinic）。

## Decisions

1. **复用 `call_clinic_agent`**  
   - 构造最小 state：`user_input`、`device_no`、`model_config`、预设 `intent_result={target_type:conversation, action:reply}`。  
   - 不设 `force_needs_history` / `skip_knowledge`（非 history 意图默认）。

2. **忽略 `conversation_id`**  
   - 非流式不再做 pending；字段可仍接收但不驱动澄清。

3. **响应固定为 conversation/reply**  
   - `content` 来自 clinic；喂养相关字段为空默认。

## Risks / Trade-offs

- **[BREAKING]** 仍期望 feeding JSON 的旧客户端会失效 → 缓解：产品确认前端已切陪伴语义。  
- **[双端分裂]** 非流式=clinic、流式=意图图 → 文档标明；后续可再收 stream。

## Migration Plan

1. 发布后非流式即走 clinic。  
2. 回滚：恢复 `analyze_intent` 原 pending + `_run_cold_intent` 逻辑。

## Open Questions

（无。）

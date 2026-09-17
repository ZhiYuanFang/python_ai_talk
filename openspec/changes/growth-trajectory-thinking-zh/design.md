## Context

成长轨迹图（`growth_trajectory_graph`）对 `confirm_prior` / `plan_next` / `generate` 等 LLM 节点使用共用 system 提示 `GROWTH_TRAJECTORY_SYSTEM_PROMPT`，并以 `thinking_enabled=True` 流式调用；`reasoning_content` 经 custom → SSE `thinking` 原样透出。

现状：system 明确「不指导思考写法」，仅约束最终 JSON/Markdown；编排字幕为中文，但模型原生思考常为英文。

## Goals / Non-Goals

**Goals:**

- 在共用 system 中明确要求：**内部思考（含提供商 reasoning 通道）使用中文**。
- 用 OpenSpec 固定该提示词行为，便于验收与后续收版。

**Non-Goals:**

- 不改 `llm_client`、不翻译英文 thinking 增量。
- 不拆分 SSE 事件类型（编排字幕 vs LLM reasoning 仍同为 `thinking`）。
- 不改图拓扑、轮次上限、各阶段 user message schema。
- 不把「中文思考」做成硬失败条件（模型偶发英文不阻断主流程）。

## Decisions

1. **只改成长轨迹 system，不改 clinic/tip/care-alert**  
   - 本次问题出在成长轨迹透出的 reasoning；范围最小。  
   - 备选：全局共用「思考用中文」——否决，避免无关模块提示词漂移。

2. **用 prompt 约束，不做后处理翻译**  
   - 成本低、与现有透传架构一致。  
   - 备选：服务端翻译 reasoning——否决（延迟、费用、语义失真）。

3. **文案落在约束列表，一句即可**  
   - 例如：`内部思考（reasoning）须使用中文。`  
   - 同步更新文件头注释，去掉「不指导思考写法」。  
   - 备选：在每个 user message 重复——否决，共用 system 已足够且避免重复。

## Risks / Trade-offs

- [模型不完全遵从] → 提示词无法 100% 保证；验收以「多数轮次中文」人工观察，不以单次英文判失败。  
- [英文 schema 枚举仍可能拉偏 CoT] → 本变更不改 `enough|ask|reconfirm` 等字段名；若仍偏英文可另开 change。  
- [字数/语气约束并存] → 当前 system 已有字数等业务句；新增一句约束，不删既有安全/schema 条款。

## Migration Plan

- 纯提示词变更，无数据迁移；部署后新会话即生效。  
- 回滚：还原 `system.py` 中该约束句与注释即可。

## Open Questions

- 无。若上线后英文仍频繁，再评估是否隐藏 LLM reasoning 或拆事件类型。

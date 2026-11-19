## Context

意图路由在识别 miss（`infer_miss_fail_kind`）后：先用规范硬文案写 miss inbox，再调用 `soft_reply_for_miss`（LLM + 画像/预测快照）替换对外 `content`。合规目标要求该出口不再带 AIGC；本轮仅改这一条路径。

## Goals / Non-Goals

**Goals:**

- miss 对外文案固定为「我只能回答信息记录相关问题」。
- 停止该路径的 LLM / 快照补算调用。
- 保留硬文案先落库与 barge miss 语义。

**Non-Goals:**

- 不改 speak_predict / speak_history 用户可见 LLM。
- 不改确认/消歧模板与 CRUD 模板。
- 不关内部分类/段维 LLM。

## Decisions

1. **固定话术常量**  
   - 文案精确：`我只能回答信息记录相关问题`（无句末标点变更，除非产品另定）。  
   - 放在常量（如 `agent_miss_soft_reply` 模块或 `segment_outcome` 旁），路由只赋值，不拼 LLM。

2. **挂钩顺序不变**  
   - 仍：`infer_miss_fail_kind` → `maybe_record_agent_miss(hard)` → 设 `miss_canonical_content` / `miss_fail_kind` → **对外 content = 固定话术**。  
   - inbox 字段继续用 hard，不用固定话术当唯一归类输入。

3. **停用 LLM 软回复实现**  
   - 路由不再 `await soft_reply_for_miss(...)`。  
   - `soft_reply_for_miss` 可改为返回固定常量（薄封装）或删除并由路由直写；优先删除/清空 LLM 与 `AGENT_MISS_SOFT_REPLY_SYSTEM_PROMPT` 引用，避免死代码再被接回。  
   - 备选「保留函数但内部 return 常量」→ 可减少路由 diff，亦可接受。

4. **确认/消歧仍跳过**  
   - `need_confirm` / options 路径不改，不写 miss、不换固定话术。

## Risks / Trade-offs

- [用户体验变硬] → 产品已接受；合规优先。  
- [近况 store 记到的 assistant 变为固定句] → 与对外一致，可接受。  
- [其它 LLM 成文仍在] → 本 change 明示非目标；若合规仍不够再开宽变更。

## Migration Plan

1. 部署 talk；miss 出口立即固定句。  
2. 回滚即恢复 LLM soft reply（有合规成本）。

## Open Questions

- （无）文案与窄范围已由产品确认。

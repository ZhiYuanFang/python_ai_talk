## Context

确认续聊 `try_handle_pending` → 用户肯定 → `leaf_intent_result` 组装字段 → `_execute_after_confirm` → `execute_history_crud` → `coerce_intent_result`。`leaf_intent_result` 与管线清确认态仍写 `"confirm_message": None`，而 `IntentResult.confirm_message: str = ""` 在 Pydantic v2 下拒绝 `None`，流式路由 500。`confirm_type: Optional[str] = None` 合法；问题仅限非 Optional 的 str 字段。

## Goals / Non-Goals

**Goals:**

- 确认后执行历史 CRUD / 落库 MUST 能把字典意图结果归一为 `IntentResult`，不因 `confirm_message is None` 崩溃。
- 源头字典与 coerce 双保险：构造处不再写 `None`；coerce 对同类字段容错。

**Non-Goals:**

- 不改确认话术内容、pending Redis 协议、Go/Flutter 契约。
- 不把所有 `str` 字段改成 `Optional[str]`（除非审计发现必须）；本变更聚焦确认清态路径已知写入点。
- 不引入测试文件。

## Decisions

1. **源头改空串**  
   `leaf_intent_result` 与 `intent_pipeline` 清确认态处：`"confirm_message": ""`（或省略依赖模型默认）。  
   *相对*：只改模型为 Optional —— 会让「无话术」在 dump 时继续出现 null，易扩散到其它消费者。

2. **coerce 归一**  
   `coerce_intent_result` 在 `model_validate` 前，对已知默认空串的 str 字段（至少 `confirm_message`，可顺带 `content`/`event_name`/`op`/`remark_keyword`/`target_type`/`action` 等同类）将 `None` 置为 `""`。  
   *相对*：仅源头修复 —— 其它路径或 LLM 偶发 null 仍可能炸。

3. **不改字段类型为 Optional**  
   保持 `confirm_message: str = ""`，语义「无确认文案 = 空串」。

## Risks / Trade-offs

- [其它 str 字段仍可能被写成 None] → coerce 对 IntentResult 中非 Optional 的 str 默认字段统一 None→""；不全量 Optional 化。  
- [漏改一处字面量] → 任务清单显式 grep `confirm_message.*None`。  
- [掩盖脏数据] → 可接受：确认清态本意即无话术。

## Migration Plan

- 部署后无需数据迁移；pending 旧值不含需改写的 confirm_message 持久语义。  
- 回滚：还原三处文件即可。

## Open Questions

- 无。若后续发现更多 ValidationError，再扩 coerce 白名单。

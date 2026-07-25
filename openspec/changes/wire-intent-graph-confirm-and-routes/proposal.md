## Why

意图分析路由已按 interrupt/confirm 与 clinic/history 后处理编写，但编译后的 `intent_graph` 仍是四节点桩图：非法 `thread_id=` 导致接口 TypeError；无 MemorySaver、未挂真实 `prepare_confirm`/`handle_feedback`；路由注入 `user_input`/`model_config` 而节点读 `text`/`model`；classify 后不按 `target_type` 分支。确认流与 conversation/history/suggest 行为均未真正落地。A/B（Redis/telemetry）已完成，现一次性把意图图接线到文档与路由期望的完整拓扑。

## What Changes

- **C0**：`ainvoke`/`astream` 改为 `config={"configurable": {"thread_id": ...}}`；confirm 不再调用不存在的 `confirm_intent` 方法
- **C1**：`compile(checkpointer=MemorySaver())`；换入真实 `prepare_confirm`（`interrupt`）与 `handle_feedback`；confirm 使用 `Command(resume=...)`
- **C2**：向量匹配与意图分类节点统一读取 `user_input` / `model_config`（与 `IntentState`、路由一致）
- **C3**：classify 后按 `target_type` 路由——feeding→确认；history→共享短链；conversation/suggest→`call_clinic_agent`；exit→END；LLM feeding（含 multi）一律进确认；修正 `call_clinic_agent` 覆盖 `target_type` 的问题
- 删除图内 stub `prepare_confirm` / `handle_confirm_feedback` / `_route_after_confirm`
- **不修改**对外 HTTP 契约字段名；**不**做 go/flutter 适配；**不**持久化 checkpointer

## Capabilities

### New Capabilities

- `intent-checkpoint-confirm`: LangGraph 检查点 + interrupt/resume 确认流（含正确 config API）
- `intent-state-field-alignment`: 意图图状态字段与路由/TypedDict 对齐（user_input、model_config）
- `intent-target-type-routing`: classify 后按 target_type 的完整后处理拓扑（feeding 确认、history、clinic）

### Modified Capabilities

（无：`openspec/specs/` 下无已归档能力需改需求；此前 `fix-confirm-flow-resume` 等为纸面完成的未接线 change，本变更以当前代码真相为准重建）

## Impact

- **代码**：`app/feeding/graphs/intent_graph.py`；`app/api/routes/intent.py`；`match_event_by_vector.py`；`classify_intent.py`；`call_clinic_agent.py`；可能触及 `thinking_messages.py`、`generate_response` 挂边
- **API**：行为补全（确认可恢复、history/suggest/conversation 有后处理）；请求/响应 schema 不变
- **依赖**：仅使用已有 `langgraph` MemorySaver / Command / interrupt
- **部署**：单 worker + 内存检查点；进程重启后未确认会话不可恢复（既有约定）
- **风险**：history/clinic 路径增加延迟；SSE + interrupt 需验证；实现按 P1→P4 里程碑顺序落地

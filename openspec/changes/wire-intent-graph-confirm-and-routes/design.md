## Context

路由层（`intent.py`）与节点文件（`prepare_confirm.py`、`handle_feedback.py`、`call_clinic_agent.py`）已按完整意图流编写，但 `intent_graph.py` 仍是桩：本地 stub 确认节点、无 checkpointer、无 `target_type` 分支。`fix-confirm-flow-resume` 等变更任务勾选完成但未真正接线；且错误地使用 `thread_id=` 顶层参数。路由注入 `user_input`/`model_config`，部分节点仍读 `text`/`model`。

约束：HTTP schema 不变；MemorySaver 内存检查点（不考虑重启恢复）；单 uvicorn worker；中文注释风格；实现按 P1→P4 顺序，便于分阶段验证。

## Goals / Non-Goals

**Goals:**
- Intent 非流式/流式不再因非法 kwargs 崩溃
- 向量中置信与 LLM feeding 均可 interrupt → 客户端 confirm/reject → resume → 飞轮/清理
- 状态字段与 IntentState 一致，向量/LLM 能读到真实用户输入
- classify 后 history / conversation / suggest / exit / feeding 各走正确后处理

**Non-Goals:**
- go_ai_talk / flutter 适配
- Redis/Postgres checkpointer
- tip_graph / clinic_graph 内部重构
- 升级 LangGraph 大版本

## Decisions

### 决策 1：检查点 API 使用 RunnableConfig（C0）

**选择**：`ainvoke(input, config={"configurable": {"thread_id": id}})`；流式同理。

**替代**：顶层 `thread_id=` —— Pregel 不接受，已在生产报错。

### 决策 2：确认恢复用 Command(resume)（C1）

**选择**：confirm 路由 `ainvoke(Command(resume=user_feedback), config=...)`；删除对 `intent_graph.confirm_intent` 的调用。

**替代**：自定义图方法封装 —— 与 LangGraph 惯例重复，且当前方法不存在。

### 决策 3：确认边拓扑（C1）

**选择**：真实 `prepare_confirm` → 始终边到 `handle_feedback` → END；删除 stub 的 `_route_after_confirm`（确认/拒绝在 resume 后由节点与 handle_feedback 处理）。

**替代**：拒绝后再进 classify —— 增加复杂度；本期保持 handle_feedback 改写 intent 后 END。

### 决策 4：字段以 IntentState 为准（C2）

**选择**：`match_event_by_vector` / `classify_intent` 改为读取 `user_input`、`model_config`；路由继续只写这两套字段。

**替代**：路由双写 `text`/`model` —— 掩盖不一致，长期更乱。

### 决策 5：post-classify 路由（C3）

| target_type | 下一跳 |
|---|---|
| feeding（含 multi） | prepare_confirm |
| history | judge_data_requirement → fetch_history → generate_response → END |
| conversation / suggest | call_clinic_agent → END |
| exit / 其他 | END |

**选择**：suggest 与 conversation 统一走 `call_clinic_agent`（不再并行维护一套 inline suggest 链）。

**替代**：suggest 单独挂 search_vectors/baby_profile —— 与 clinic 重复拉数。

### 决策 6：call_clinic_agent 返回形状（C3）

**选择**：合并 clinic 结果时**保留**进入节点前的 `intent_result.target_type`（及既有喂养字段），仅补充回答内容到约定字段（`response` 和/或 `intent_result.content`），供路由把 history/suggest 的 `content` 填好。

**替代**：继续强制改写为 conversation —— 破坏 suggest 语义与路由分支判断。

### 决策 7：实施里程碑

| 阶段 | 范围 | 可验证结果 |
|---|---|---|
| P1 | C0+C1+C2 | 不崩；向量中置信确认可 resume；字段对齐 |
| P2 | C3a | classify→feeding→确认 |
| P3 | C3b | history 链出回答 |
| P4 | C3c | conversation/suggest→clinic；修 target_type |

## Risks / Trade-offs

| 风险 | 缓解 |
|---|---|
| 一次改动面大、难排障 | 严格按 P1→P4 apply；每阶段冒烟后再进下一阶段 |
| history/clinic 延迟上升 | 接受产品语义；监控超时；闸门已修 |
| astream + interrupt 行为差异 | P1 同时测非流式与流式确认 |
| MemorySaver 重启丢会话 | 文档化；与既有约定一致 |
| generate_response / clinic 字段耦合 | P3/P4 对照 ClinicState 映射表改，避免臆测 |

## Migration Plan

1. 按 P1→P4 合入同一 change 的代码
2. 重建部署后验证：analyze（崩点消失）→ 中置信确认 → confirm/reject → history/conversation/suggest
3. 回滚：回退镜像；无数据迁移

## Open Questions

1. reject 后是否需要返回固定致歉话术以外的再分类？（本期：handle_feedback 现有逻辑，不重进 classify）
2. 流式 thinking 文案是否为 history/clinic 新节点补全？（建议 P3/P4 同步补 `thinking_messages`）

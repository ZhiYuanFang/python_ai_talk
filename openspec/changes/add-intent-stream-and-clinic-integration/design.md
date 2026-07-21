## Context

当前系统已完成喂养意图向量匹配增强（enhance-feeding-intent-vector-matching 变更），包含向量匹配、用户确认机制和数据飞轮。但 intent 接口仍为非流式返回，无法暴露 LangGraph 节点执行进度。

clinic 接口已实现流式 SSE 返回，通过 `thinking` 事件暴露节点思考过程，通过 `answer` 事件返回最终结果。intent 接口需要对齐这一体验。

此外，当意图识别为"喂养建议"（conversation/suggest）时，当前需要前端发起二次请求调用 clinic 接口。应在 intent 流程内部直接调用 clinic agent 获取回答，减少前端交互。

## Goals / Non-Goals

**Goals:**

1. intent 接口支持 stream 参数（默认 false），true 时通过 SSE 返回
2. 流式响应暴露节点思考进度（向量匹配、LLM 分类、确认等）
3. intent 喂养建议节点内部调用 clinic agent 获取回答
4. 调研 confirm 接口在 go_ai_talk 和 flutter_ai_talk 中的适配需求

**Non-Goals:**

1. 不修改 clinic 接口的现有流式实现
2. 不修改向量匹配和确认机制的核心逻辑
3. 不实现 go_ai_talk 和 flutter_ai_talk 的代码修改（仅调研）

## Decisions

### 决策 1：stream 参数实现方式

**选择**：新增 `/v1/analyze/intent/stream` 端点，而非在现有端点增加参数

**理由**：
- 与 clinic 接口结构一致（clinic 有独立的 `/v1/clinic/stream`）
- 非流式和流式逻辑分离，便于维护
- 避免在同一个端点中处理两种响应格式

### 决策 2：thinking 事件设计

**选择**：复用 clinic 的 thinking 事件格式

```
event: thinking
data: {"node": "match_event_by_vector", "message": "正在匹配喂养事件...", "status": "running"}
```

**节点 thinking 消息映射**：
- `match_event_by_vector` → "正在匹配喂养事件..."
- `classify_intent` → "正在分析意图..."
- `prepare_confirm` → "正在生成确认话术..."
- `handle_feedback` → "正在处理用户反馈..."
- `call_clinic_agent` → "正在获取喂养建议..."

### 决策 3：clinic agent 内部调用方式

**选择**：在 intent_graph 中新增 `call_clinic_agent` 节点，直接调用 clinic_graph

**理由**：
- 避免 HTTP 二次请求开销
- 共享同一进程内的状态和上下文
- clinic_graph 已封装为可复用的图实例

### 决策 4：confirm 接口适配调研

**选择**：作为 tasks 中的首个任务，先调研再实现

**调研范围**：
- go_ai_talk：检查意图分析调用逻辑，确认是否需要处理 confirm 响应
- flutter_ai_talk：检查 UI 交互流程，确认是否需要增加确认弹窗

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| clinic agent 内部调用增加 intent 响应时间 | 用户等待时间变长 | 流式返回 thinking 进度，缓解感知延迟 |
| confirm 接口适配需要兄弟仓修改 | 跨仓协调成本 | 调研后输出适配文档，由用户手动修改 |
| 流式和非流式逻辑重复 | 维护成本 | 共享核心节点逻辑，仅路由层不同 |

## Open Questions

1. confirm 接口是否需要 go_ai_talk 修改调用逻辑？（待调研）
2. flutter_ai_talk 是否需要新增确认 UI 组件？（待调研）
3. clinic agent 内部调用时如何传递上下文？（设计时确定）

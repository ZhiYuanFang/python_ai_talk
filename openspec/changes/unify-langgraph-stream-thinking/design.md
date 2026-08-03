## Context

现状：`clinic_graph` / `tip_graph` / `intent_graph` 仍用 LangGraph 定义；非流式与 `call_clinic_agent` 走 `ainvoke`。流式为 progressive「先报后做」在路由层手搓 `run_*_with_thinking` + 步骤表/条件循环，与图边双轨（含 `needs_history` 门禁后的动态 prepare）。progressive-stream-thinking 当时只否定了 `astream(updates)` 事后报，未采用 `custom` writer。

约束：Python 3.12；SSE 契约不变；保留逐步 thinking 文案映射；`clinic-needs-history-gate` 条件边留在图内；最终 token 流可继续图外。

## Goals / Non-Goals

**Goals:**

- 流式与非流式共用同一编译图作为编排真相
- 流式在节点业务逻辑开始前推送对应 thinking（先报后做）
- 删除（或不再作为主路径）路由层对准备/意图节点的第二份执行表
- 嵌套 clinic 准备在 intent 流式下仍可见逐步 thinking（或等价合并边界）

**Non-Goals:**

- 不把最终回答 token 流强行塞进返回 dict 的 StateGraph 节点（可继续 `stream_response`）
- 不改 Go/Flutter SSE 字段协议
- 不借机更换 langgraph 大版本或换编排框架
- 不削弱 needs_history / skip_knowledge 等已有图语义

## Decisions

### 1. 统一编排 = 图为唯一执行器

- **选择**：流式准备/意图阶段 `graph.astream(...)`；非流式 `graph.ainvoke(...)`；禁止路由再 await 同一批准备节点函数作为主路径
- **理由**：消灭双轨；门禁等条件边只维护一份
- **替代**：继续手搓 steps — 否决；或删图只留 runner — 与「保留 LangGraph」决策不符

### 2. 逐步 thinking = `custom` + 节点内先 write

- **选择**：节点包装或节点开头 `get_stream_writer()`（3.12 async 可用），在 await 业务前 `writer({"type":"thinking","node": name, "content": msg})`；`stream_mode` 含 `"custom"`（可与 `updates` 组合取终态）
- **理由**：满足先报后做且不依赖 updates 完成事件；ainvoke 无消费者时 writer 无害
- **替代**：`astream_events` on_chain_start — 事件噪声大、嵌套 LLM 易误报；手搓 — 已否决
- **包装优先**：`with_node_thinking(node_name, fn)` 集中映射 `get_thinking_message`，避免每个节点复制

### 3. 路由只做 formatter

```
yield SSE ← custom thinking chunks
state 累积 ← updates 或 astream 结束后取值
然后 stream_response / 组装 intent answer
```

- tip：流式改走 `tip_graph.astream`（与硬编码 data_requirement 兼容：可预置 state 后仍进图，或图入口跳过已满足的 judge）
- clinic：飞轮纳入图节点，或图前单次 thinking + 其后整图 astream（避免飞轮静默）；优先「飞轮进图」以保持单一边界

### 4. 嵌套 clinic

- **选择**：`call_clinic_agent` 在流式上下文对 `clinic_graph` 使用 `astream(custom)` 并向调用方转发 custom；或把 clinic 数据准备提升为 intent 可组合子图且 stream 穿透
- **理由**：外层 intent `astream` + 内层 `ainvoke` 会吞掉内层逐步字幕
- **非流式**：内层保持 `ainvoke` 即可

### 5. 与 progressive / needs-history 的关系

- 产品：保留 progressive「每步先 thinking」语义
- 实现：替换手搓为 LangGraph custom
- needs_history：仅依赖 `clinic_graph` 条件边；删除 clinic 路由动态拼 steps

### 6. Spike 先行

- **选择**：tasks 首项对单节点（如 `judge_needs_history`）验证 custom 在 LLM 返回前到达 SSE
- **理由**：历史上 async writer 有过 context 问题；先证伪再铺全

## Risks / Trade-offs

- [async custom 偶发丢事件] → Spike + 必要时节点签名注入 `writer`；单测 mock writer
- [嵌套流转发复杂] → 抽 `forward_graph_custom_stream`；或短期 intent→clinic 合并 thinking 粒度
- [tip 硬编码 vs tip_graph 入口含 judge] → 预置 `data_requirement` 时跳过 judge 或 force 路径与现 tip 对齐
- [包装漏网节点无字幕] → 注册节点清单与 thinking_messages key 对齐检查
- [与手搓短暂并存] → 迁移完成即删路由步进，避免三轨

## Migration Plan

1. Spike custom writer
2. 包装共享准备节点 + clinic_graph 流式切换
3. tip_graph、intent_graph + 嵌套转发
4. 删除 clinic/tip/intent 主路径手搓 prepare；回归 SSE 逐步顺序与非流式 JSON
5. 回滚：恢复 progressive_thinking 步进（git revert）或临时开关（若需要可加，非必须）

## Open Questions

- tip 流式是否必须跑 `judge_data_requirement`，还是继续预置 `data_requirement` 并从 `fetch_history` 作为子入口（LangGraph 多入口或预置后短路径）— 实现时选改动最小且与「强制需要历史」一致的方案

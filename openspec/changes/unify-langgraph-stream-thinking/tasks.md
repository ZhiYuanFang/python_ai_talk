## 1. Spike and shared helpers

- [x] 1.1 Spike：单节点 + `astream(stream_mode="custom")`，确认 thinking 在 LLM/HTTP await 之前到达；记录 Python 3.12 下 `get_stream_writer` 用法
- [x] 1.2 新增节点包装（如 `with_node_thinking`）与 custom payload 约定（node / content）；ainvoke 安全无消费者
- [x] 1.3 新增「消费 graph custom → SSE thinking」小辅助，供 clinic/tip/intent 路由复用

## 2. Clinic path

- [x] 2.1 为 clinic 准备链节点挂上 thinking 包装（含 `judge_needs_history` 等）；跳过节点不发对应 fetch 文案
- [x] 2.2 隐式飞轮纳入图或图前明确单次 thinking，避免图外静默长耗时
- [x] 2.3 `/v1/clinic/stream` 改为 `clinic_graph.astream`（custom±updates）驱动准备，删除动态 prepare_steps 主路径；其后仍 `stream_response`
- [x] 2.4 确认 needs_history / skip_knowledge 仅由图条件边表达，流式与 ainvoke 行为一致

## 3. Tip path

- [x] 3.1 对齐 tip 预置 `data_requirement` 与 tip_graph 入口（跳过多余 judge 或短路径），保持「强制需要历史」
- [x] 3.2 `/v1/tip/stream` 改为 `tip_graph.astream` + custom thinking，删除线性 prepare_steps 主路径；其后仍 `stream_tip_response`

## 4. Intent path and nesting

- [x] 4.1 intent 冷启动流式改为 `intent_graph.astream`，删除手写 `route_after_*` 执行循环主路径（路由函数仍可供图内条件边使用）
- [x] 4.2 `call_clinic_agent`：流式上下文对 clinic 准备 astream 并转发 custom；非流式保持 ainvoke
- [x] 4.3 非流式 `/intent` 回归：仍 ainvoke，行为与改前一致

## 5. Cleanup and verify

- [x] 5.1 移除或降级路由对 `run_linear_steps_with_thinking` / `run_one_step_with_thinking` 的主路径依赖；更新过时注释
- [x] 5.2 单测：writer 包装、custom 先于业务；门禁跳过无 fetch thinking；嵌套转发（可 mock）
- [x] 5.3 手测 clinic/tip/intent 流式逐步字幕顺序与非流式 JSON；确认 SSE 字段未变

# Proposal: fix-confirm-flow-resume

## 变更名称
fix-confirm-flow-resume

## 概述
修复 python_ai_talk 意图分析 confirm 流程的 3 个核心 Bug，使 LangGraph 的 interrupt + Command(resume) 机制能够正确工作，让喂养意图的用户确认/拒绝流程真正跑通。

## 背景
当前 `add-intent-stream-and-clinic-integration` 变更完成后，发现 confirm 流程存在 3 个阻断性 Bug：

1. **prepare_confirm 节点未生成 conversation_id**：返回的状态只有 `need_confirm` 和 `confirm_message`，没有 `conversation_id`，导致 confirm 接口无法恢复中断的图执行
2. **handle_feedback 节点无入边**：`intent_graph.py` 中 `prepare_confirm → END` 直连，`handle_feedback` 成为孤儿节点，即使恢复了中断也无法执行数据飞轮/删除向量逻辑
3. **ainvoke 未传 thread_id**：路由层 `intent_graph.ainvoke(initial_state)` 没有传 `thread_id`，MemorySaver 不会保存检查点，confirm 接口无法恢复

## 目标
- 使用 LangGraph 0.2.x 的 `interrupt()` + `Command(resume=...)` 机制替换当前错误的 END 直连方案
- 确保 prepare_confirm 节点生成 conversation_id 并通过 interrupt 中断图执行
- 确保 handle_feedback 节点在恢复后正确执行
- 确保路由层正确传递 thread_id 并从中断状态提取确认信息
- 确保流式接口在中断时正确返回确认事件

## 范围
**本次仅修复 python 侧的 3 个 Bug**，不涉及 go_ai_talk 和 flutter_ai_talk 的适配（后续独立变更处理）。

## 非目标
- 不修改 go_ai_talk 的调用逻辑（走 WS 模式适配在独立变更）
- 不修改 flutter_ai_talk 的 UI/Repository（在独立变更）
- 不修改 clinic 模块的任何代码
- 不修改 intent_graph 的节点拓扑（除了 prepare_confirm → handle_feedback 边）
- 不考虑服务重启后中断状态丢失的问题（按 project_memory 约定，不考虑）

## 设计决策
- **中断机制**：使用 LangGraph 0.2.x 的 `interrupt()` 函数（从 `langgraph.types` 导入），而非旧版 `interrupt_before` 配置
- **恢复机制**：使用 `Command(resume=value)`（从 `langgraph.types` 导入）恢复中断的图执行
- **conversation_id 生成**：在路由层生成 `thread_id`（uuid4），传给 `ainvoke`，同时作为 `conversation_id` 返回给客户端
- **checkpointer**：继续使用 MemorySaver（内存态，按 project_memory 约定不考虑持久化）

## 风险
- LangGraph 0.2.x 的 interrupt 机制在流式模式（astream）下的行为需要验证
- interrupt 后 astream 是否会正确 yield 中断状态需要测试

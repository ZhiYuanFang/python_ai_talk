# Tasks: fix-confirm-flow-resume

## 1. prepare_confirm 节点修复
- [x] 1.1 在 `app/feeding/graphs/nodes/prepare_confirm.py` 中导入 `interrupt`（从 `langgraph.types`）和 `uuid4`
- [x] 1.2 生成 conversation_id（使用 uuid4），写入 state
- [x] 1.3 调用 `interrupt()` 中断图执行，传递 need_confirm/confirm_message/conversation_id
- [x] 1.4 interrupt 恢复后，将 user_feedback 写入 state 并返回

## 2. intent_graph 图拓扑修复
- [x] 2.1 在 `app/feeding/graphs/intent_graph.py` 中将 `prepare_confirm → END` 改为 `prepare_confirm → handle_feedback`
- [x] 2.2 添加 `handle_feedback → END` 边
- [x] 2.3 删除 `IntentGraph.confirm_intent` 方法（改用 ainvoke + Command 恢复）

## 3. 路由层修复（非流式）
- [x] 3.1 在 `app/api/routes/intent.py` 的 `analyze_intent` 中生成 thread_id（uuid4）
- [x] 3.2 将 thread_id 传给 `intent_graph.ainvoke(state, thread_id=thread_id)`
- [x] 3.3 从 ainvoke 返回状态中检测 `__interrupt__` 字段，提取确认信息
- [x] 3.4 中断时返回 IntentResponse(need_confirm=True, conversation_id=thread_id)

## 4. 路由层修复（流式）
- [x] 4.1 在 `analyze_intent_stream` 中生成 thread_id（uuid4）
- [x] 4.2 将 thread_id 传给 `intent_graph.astream(state, thread_id=thread_id)`
- [x] 4.3 astream 遍历结束后，从 final_state 检测 `__interrupt__` 字段
- [x] 4.4 中断时推送 answer 事件包含 need_confirm=True

## 5. confirm 接口修复
- [x] 5.1 在 `confirm_intent` 路由中导入 `Command`（从 `langgraph.types`）
- [x] 5.2 用 `Command(resume=request.user_feedback)` 恢复图执行
- [x] 5.3 从恢复后的最终状态提取意图结果
- [x] 5.4 删除对 `intent_graph.confirm_intent` 方法的调用

## 6. 验证
- [x] 6.1 验证非流式请求在置信度 90%-95% 时返回 need_confirm=True 和有效 conversation_id
- [x] 6.2 验证流式请求在中断时推送 answer 事件包含 need_confirm=True
- [x] 6.3 验证 confirm 接口用 conversation_id 恢复图执行并返回最终意图结果
- [x] 6.4 验证 handle_feedback 在 confirm 后执行数据飞轮、在 reject 后删除向量

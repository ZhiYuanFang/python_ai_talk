## 1. 调研：confirm 接口适配分析

- [x] 1.1 调研 go_ai_talk 意图分析调用逻辑，确认是否需要处理 need_confirm 响应
- [x] 1.2 调研 go_ai_talk 是否需要调用 `/v1/analyze/intent/confirm` 接口
- [x] 1.3 调研 flutter_ai_talk UI 交互流程，确认是否需要新增确认弹窗组件
- [x] 1.4 输出适配需求文档，记录调研结论

## 2. intent 流式响应实现

- [x] 2.1 创建 `app/feeding/graphs/nodes/stream_intent_response.py`，实现流式响应节点
- [x] 2.2 创建 `app/feeding/graphs/nodes/thinking_messages.py`，定义 intent 节点的 thinking 消息映射
- [x] 2.3 新增 `/v1/analyze/intent/stream` API 端点，支持 SSE 流式返回
- [x] 2.4 修改 `app/feeding/graphs/intent_graph.py`，添加流式 thinking 事件发送逻辑
- [x] 2.5 更新 `app/feeding/schemas/intent.py`，添加流式响应相关数据模型

## 3. clinic agent 内部调用

- [x] 3.1 创建 `app/feeding/graphs/nodes/call_clinic_agent.py`，实现 clinic agent 调用节点
- [x] 3.2 修改 `app/feeding/graphs/intent_graph.py`，在 conversation/suggest 意图路由中添加 call_clinic_agent 节点
- [x] 3.3 确保 clinic_graph 可被 intent_graph 内部调用，传递必要的上下文
- [x] 3.4 处理 clinic agent 调用失败时的降级逻辑

## 4. 集成和验证

- [x] 4.1 验证非流式 intent 请求正常工作（向后兼容）
- [x] 4.2 验证流式 intent 请求正确发送 thinking 事件
- [x] 4.3 验证 conversation/suggest 意图正确调用 clinic agent
- [x] 4.4 验证 confirm 接口在流式模式下正常工作
- [x] 4.5 更新 `docs/deploy-guide.md`，添加 intent stream 接口说明

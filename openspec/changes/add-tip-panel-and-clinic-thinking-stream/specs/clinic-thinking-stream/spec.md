## ADDED Requirements

### Requirement: clinic_graph 执行过程流式思考展示
系统 SHALL 将 `clinic_graph` 的执行方式从 `graph.ainvoke()` 改为 `graph.astream()`，在每个节点开始执行时推送 `thinking` 类型的 SSE 事件，让用户实时感知 AI 的思考过程。

#### Scenario: 诊疗请求触发节点级思考事件流
- **WHEN** 客户端调用 `/v1/clinic/stream` 接口发起诊疗请求
- **THEN** 系统 SHALL 依次推送以下 SSE 事件：judge_data_requirement 节点的 thinking 事件 → fetch_history 节点的 thinking 事件 → search_vectors 节点的 thinking 事件 → fetch_baby_profile 节点的 thinking 事件 → LLM 流式回答的 answer 事件 → [DONE] 结束标记

#### Scenario: 节点思考文案映射
- **WHEN** clinic_graph 的各节点开始执行
- **THEN** 系统 SHALL 推送对应中文思考文案：judge_data_requirement → "正在分析需要哪些历史数据..."、fetch_history → "正在拉取最近的喂养记录..."、search_vectors → "正在检索知识库中的相关知识..."、fetch_baby_profile → "正在获取宝宝画像信息..."、LLM 开始 → "正在生成回答..."

#### Scenario: 节点执行失败时思考流程不中断
- **WHEN** clinic_graph 中某个节点（如 search_vectors）执行失败但有 fallback
- **THEN** 系统 SHALL 推送该节点的 thinking 事件后继续执行后续节点，不中断思考事件流

#### Scenario: thinking 事件与 answer 事件格式一致
- **WHEN** 系统推送 SSE 事件
- **THEN** thinking 事件和 answer 事件 SHALL 使用相同的 JSON 结构 `{"type": "thinking|answer", "content": "..."}`，前端可统一处理

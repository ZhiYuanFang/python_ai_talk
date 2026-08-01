## 1. 共享与 clinic / tip

- [x] 1.1 抽取线性「先 thinking 再 await 节点」辅助（可选 shared），或在路由内清晰步骤循环；每步 yield 后可 `asyncio.sleep(0)`
- [x] 1.2 改写 `clinic.py` 流式：飞轮先 thinking 再判定；数据准备逐步执行；再 `llm_start` + `stream_response`
- [x] 1.3 改写 `tip.py` 流式：judge→history→vectors→profile→derive_baby_age 逐步先报后做；再 llm_start + stream

## 2. Intent stream

- [x] 2.1 将 `_route_after_vector_match` / `_route_after_classify` 置于可被路由 import 的位置（若尚在 graph 模块内则导出）
- [x] 2.2 改写 `_stream_intent_response`：按路由逐步先 thinking 再执行节点，分支与现图一致；最后组装 answer SSE
- [x] 2.3 确认非流式 `analyze_intent` 仍可用 `intent_graph.ainvoke`（行为不变）

## 3. 文案

- [x] 3.1 为 clinic 飞轮步骤补充 thinking 文案（thinking_messages）；核对 intent/tip/clinic 节点名均有映射

## 1. 共享飞轮与闺蜜同步生成

- [x] 1.1 抽取或复用 clinic 隐式飞轮为 shared 函数（device_no + user_text + model_config），供 clinic 路由与 `call_clinic_agent` 共用
- [x] 1.2 新增/复用同步闺蜜生成（`clinic_answer` + `llm_client.invoke`，输入含 chat_context / history / knowledge / baby_profile）；可基于 `stream_response` 拼装逻辑

## 2. 改造 `call_clinic_agent`（A/B/C/D）

- [x] 2.1 生成前调用隐式飞轮（失败不阻断、不误标 applied）
- [x] 2.2 按 device_no 读 companion session，注入 `clinic_state.chat_context`
- [x] 2.3 `clinic_graph.ainvoke` 后改走闺蜜同步生成；conversation/suggest 不再调用 `generate_response`
- [x] 2.4 成功非兜底时 `append_turn`（source=`intent`）并更新 `last_suggestion` + knowledge ids；兜底不写会话
- [x] 2.5 确认 history 短链仍用 `generate_response`；feeding/pending 不碰 companion

## 3. 校验

- [x] 3.1 手工或日志核对：tip → intent conversation → clinic 近轮互相可见；飞轮对 tip 开场可触发

## 1. P1 — C2 字段对齐

- [x] 1.1 修改 `match_event_by_vector.py`：从 `user_input` 读取文本（兼容可读 `text` 作 fallback 可选），加中文注释
- [x] 1.2 修改 `classify_intent.py`：从 `user_input` / `model_config` 读取，去掉对 `text` / `model` 的唯一依赖

## 2. P1 — C0/C1 检查点与确认接线

- [x] 2.1 重写 `intent_graph.py`：导入真实 `prepare_confirm`、`handle_feedback`；删除 stub 与 `_route_after_confirm`；边 `prepare_confirm → handle_feedback → END`；`compile(checkpointer=MemorySaver())`
- [x] 2.2 修改 `intent.py` 非流式/流式：`config={"configurable": {"thread_id": thread_id}}` 替代 `thread_id=`
- [x] 2.3 修改 confirm 路由：`ainvoke(Command(resume=...), config=...)`；删除 `intent_graph.confirm_intent(...)`
- [x] 2.4 冒烟：向量中置信路径可返回 need_confirm；confirm/reject 可 resume 且无 TypeError

## 3. P2 — C3a LLM feeding 确认

- [x] 3.1 在 `intent_graph.py` 增加 `_route_after_classify`：`feeding` → `prepare_confirm`；其余暂可 END（待 P3/P4 扩展）
- [x] 3.2 确认 `classify_intent` 对 feeding/multi 写出足够 `intent_result` 供确认话术使用
- [x] 3.3 冒烟：LLM 分类为 feeding 时进入确认 interrupt

## 4. P3 — C3b history 短链

- [x] 4.1 将 `judge_data_requirement`、`fetch_history`、`generate_response` 挂入意图图，边顺序正确
- [x] 4.2 `_route_after_classify`：`history` → 上述短链 → END
- [x] 4.3 确保路由能从 `state.response`（或约定字段）填充 history 的 `content`；补 `thinking_messages` 如需要
- [x] 4.4 冒烟：history 意图返回非空回答内容

## 5. P4 — C3c clinic 与 suggest/conversation

- [x] 5.1 挂入 `call_clinic_agent`；`_route_after_classify`：`conversation`/`suggest` → 该节点；`exit` → END
- [x] 5.2 修正 `call_clinic_agent`：保留原 `target_type`；回答写入路由可读字段
- [x] 5.3 补 thinking 文案；冒烟 conversation/suggest 有回答且 suggest 的 target_type 保持

## 6. 收尾验证

- [x] 6.1 回归：高置信向量直接返回、exit、拒绝反馈、流式 analyze 中断事件
- [x] 6.2 确认无残留 stub/`confirm_intent`/`thread_id=` 调用

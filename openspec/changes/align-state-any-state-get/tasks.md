## 1. Shared：State 入参与读取

- [x] 1.1 将 `qa_fast_path.is_block_fast_path` 改为 `state: Any`，字段经 `state_get` 读取
- [x] 1.2 将 `companion_session.derive_history_grounded` 改为 `state: Any`，字段经 `state_get` 读取
- [x] 1.3 对齐 `progressive_thinking`：`state`/`NodeFn` 入参为 `Any`，合并补丁改用 `apply_state_patch`（去掉对 `dict.update` 的假定）

## 2. Clinic：假 Dict 注解与不安全读取

- [x] 2.1 `search_qa_fast_path`：注解 `Any`，体内 `.get` 改为 `state_get`
- [x] 2.2 `format_qa_answer`：注解 `Any`，体内 `.get` 改为 `state_get`
- [x] 2.3 `prompts/clinic_answer.resolve_clinic_needs_history`：注解 `Any`，体内 `.get` 改为 `state_get`
- [x] 2.4 其余 clinic 节点假 `Dict` 注解改为 `Any`（已用 `state_get` 的仅改注解）：`rewrite_standalone_question_node`、`generate_clinic_answer`、`generate_response`、`stream_response`、`stream_response_node`、`implicit_feedback`

## 3. Tip / Care-alert

- [x] 3.1 `tip`：`stream_tip_response` 注解改为 `Any`（读字段已走 `state_get` 则仅改注解）
- [x] 3.2 `care_alert`：`generate_care_alerts` 注解改为 `Any`
- [x] 3.3 `care_alert`：`resolve_baby_age` 注解改为 `Any`，预置月龄经 `state_get` 读取（去掉 `in state` + `.get`）

## 4. 验收扫尾

- [x] 4.1 在 `app/` 下确认图 State 入口无残留 `state: Dict[str, Any]`（允许非 State 的其它 dict 参数）
- [x] 4.2 在图节点与 shared 读 State 路径确认无残留对整包 `state.get(` / `in state` 主路径用法
- [x] 4.3 相关改动补全中文业务注释（方法级说明入参可为 Pydantic 或 dict）

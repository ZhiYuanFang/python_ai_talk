## 1. Shared gate node

- [x] 1.1 新增 `app/shared/graphs/nodes/prompts/needs_history.py`：宽松布尔判定提示词，仅输出 `{"needs_history": true|false}`，含中文业务注释
- [x] 1.2 新增 `app/shared/graphs/nodes/judge_needs_history.py`：读 question/user_input；尊重 `force_needs_history`；LLM/解析失败默认 true；写出 `needs_history`
- [x] 1.3 可选：`fetch_history` 在 `needs_history is False` 且未 force 时防御性返回 `[]` 且不打 API（主路径仍应跳过节点）

## 2. State and clinic graph

- [x] 2.1 `ClinicState`（必要时 Intent 经 clinic 的初始 state 注释）增加 `needs_history`、`force_needs_history`
- [x] 2.2 改造 `clinic_graph`：入口 `judge_needs_history`；条件边进入 `judge_data_requirement`→`fetch_history` 或跳到 `search_vectors` /（`skip_knowledge`）`fetch_baby_profile`；`history_events` 在跳过路径置空
- [x] 2.3 抽取「是否继续拉历史」小函数供 graph 与路由共用，避免双份条件漂移

## 3. Clinic stream and thinking

- [x] 3.1 改造 `clinic.py` prepare：先跑 `judge_needs_history`（thinking），再按结果动态拼接 scope+fetch 与后续步骤
- [x] 3.2 更新 clinic `thinking_messages`：门禁 / 范围 / 拉取三条文案分离；确认跳过拉取时不推送 fetch 文案

## 4. Upstream force

- [x] 4.1 `call_clinic_agent`：`target_type=history` 时设 `force_needs_history=true`（或等价跳过门禁入口），保证仍拉历史且保留 `skip_knowledge`
- [x] 4.2 确认 tip 流式不挂 `judge_needs_history`，硬编码 `data_requirement`→`fetch_history` 行为不变
- [x] 4.3 若 `tip_graph` 仍导出：入口不挂门禁，文档/注释与流式路径一致

## 5. Verify

- [x] 5.1 手测或单测：闲聊/纯知识 → `needs_history=false`、无 history HTTP；喂养相关/查记录 → true 且仍有 scope+fetch
- [x] 5.2 手测：intent history 与 tip 仍能拿到历史；clinic 图 `skip_knowledge` 与门禁组合不互踩

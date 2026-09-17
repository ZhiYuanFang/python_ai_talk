## 1. 全局约束文档

- [x] 1.1 在 `openspec/project.md` 新增「LLM Agent 提示词与流式约定」：强制每模块 `prompts/system.py`、中文思考/输出、对外 SSE 必须 `llm_client.stream`、禁止新建 tip/外置 prompt 飞轮
- [x] 1.2 更新 `AGENTS.md` 摘要上述约定；修正 project.md 中过时 tip/通识向量库必建表述

## 2. Go 校对与清理（`d:\work\go_ai_talk`）

- [x] 2.1 全仓 grep tip / TipStream / `/v1/tip` / `/device/tip`；确认无业务入口（或删除残留）且 clinic/care-alert/intent 不受影响
- [x] 2.2 清理本仓 `scripts/patch_go_*`、`create_go_*` 中 tip 相关生成片段，避免误用

## 3. 删除 Python tip

- [x] 3.1 删除 `app/tip/**`、`app/api/routes/tip.py` 及 routes 挂载；更新 companion 去掉 tip 开场写入
- [x] 3.2 更新 README / deploy-guide 去掉 tip API 与 tip_graph 说明

## 4. care_alert 内联 system

- [x] 4.1 新增 `care_alert/.../prompts/system.py`：迁入当前 `prompt.json` 的 `output_format` + 中文思考约束
- [x] 4.2 `care_alert_analyze` 改用常量；删除 `prompt_store`、`data/care_alert/prompt.json`；去掉 `care_alert_prompt_dir` 与 compose care_alert 卷（若仅服务 prompt）

## 5. 各模块 system.py + 中文

- [x] 5.1 `clinic/.../prompts/system.py`：抽出 clinic system，含中文思考；`clinic_answer` 引用之
- [x] 5.2 `feeding/.../prompts/system.py`：意图分类等 system 常量 + 中文约束
- [x] 5.3 `shared/.../prompts/system.py`：`needs_history` / `data_requirement` 常量 + 中文约束；调用方改引用
- [x] 5.4 核对 `growth_trajectory/.../prompts/system.py` 已含中文思考，与全局约定一致

## 6. 对外流式审计

- [x] 6.1 审计 clinic stream、care-alert analyze/stream、growth turn、intent stream：主 LLM 均为 `stream`；同步 clinic 可保留 invoke
- [x] 6.2 确认无「invoke 全文再假 SSE」路径

## 7. 验收

- [x] 7.1 grep：无 tip 路由/包；无 prompt_store/prompt.json 加载；各存活模块存在 `system.py`
- [x] 7.2 手工点 clinic stream / care-alert stream（若环境可用）确认 thinking 中文倾向与业务正常

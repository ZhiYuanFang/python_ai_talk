## 1. Gateway workspaces（先于删代码）

- [x] 1.1 创建 `deploy/openclaw/workspaces/intent/`：AGENTS.md（tool-calling 原则；禁止 JSON 信封照搬）
- [x] 1.2 创建 `deploy/openclaw/workspaces/clinic/`：只读 + 隐式采纳 tool 指引；无写史
- [x] 1.3 创建 `deploy/openclaw/workspaces/care_alert/`：拉史→推理→强制 `emit_care_cards`；无飞轮、无通识编造
- [x] 1.4 更新 `deploy/openclaw/openclaw.json5` 指向上述 workspace 路径并核对 tools.allow

## 2. README / 文档

- [x] 2.1 重写 `README.md`：LangGraph→OpenClaw 部署对照表 + Gateway/Python/Go 最短步骤与 curl 验收（禁止散文与旧 analyze API）
- [x] 2.2 `docs/deploy-guide.md` 文首声明以 README 为准，或删除冲突的旧智能体部署段

## 3. Python 删除死代码

- [x] 3.1 删除 Care 算卡链（`generate_care_alerts`、相关 prompts/compact、`analyze` 产品路径）与 Care 飞轮（`prompt_flywheel`/`flywheel_store`/facade care 方法）
- [x] 3.2 删除空 `*/agents`、空 `*_graph.py` 壳
- [x] 3.3 删除无入口 Intent/Clinic 图节点与 `intent_pipeline` 等；保留飞轮所需 `intent_cache_store`/`qa_fast_path`/`suggestion_acceptance`/`companion_session` 等
- [x] 3.4 更新 `openspec/project.md` 目录表述（Care 无 Python 生成；无进程内 agents）
- [x] 3.5 静态检索：无 `/v1/analyze`、`run_agent_steps`、Care 飞轮可调用路径；`/v1/tools` 与 knowledge 仍可 import

## 4. Go 对齐新 Python（审计 + 收尾）

> **提案时审计（2026-08-15）**：Intent/Clinic/Care **业务路径已**改 `OpenClawFromCfg()`；`PythonAIClientFromCfg` **已无调用方**；`python_ai_client.go` 与 compose 中 `PYTHON_AI_TALK_URL` 仍为误导残留；Go 配置示例中 **未见** `openclaw.gatewayUrl` 键（仅环境变量可读）。

- [x] 4.1 再确认 voice 树无对 Python `/v1/analyze|clinic|care-alert` 的业务调用
- [x] 4.2 删除或拆分 `python_ai_client.go` 编排方法；`CareAlertAnalyzeItem` 等仍用类型迁到独立文件
- [x] 4.3 manifest/compose/配置示例补齐 `OPENCLAW_GATEWAY_URL`/`TOKEN`；弱化 `PYTHON_AI_TALK_URL` 编排暗示
- [x] 4.4 编译 `go build` 相关包通过

## 5. 验收（无测试文件）

- [x] 5.1 README 对照表与最短启动命令可读；无旧 analyze 入口误导
- [x] 5.2 workspaces 与 json5 路径一致；Care/Intent/Clinic ACL 符合 spec
- [x] 5.3 Python 保留面可启动（手工或 import）；Go 无死客户端误导

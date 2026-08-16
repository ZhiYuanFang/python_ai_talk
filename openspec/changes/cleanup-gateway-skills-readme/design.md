## Context

`openclaw-gateway-direct` 已完成：Go 产品路径打 Gateway；Python 删除 `/v1/analyze|clinic|care-alert` 编排路由并暴露 `/v1/tools/*`。残留：Intent/Clinic/Care 图节点与 pipeline、Care Python 算卡、Care 飞轮、空 agents 壳、README 仍写 LangGraph。explore 已锁定：Care 算力全交 Gateway skill；Intent 提炼原则迁 workspace 再删；README 短对照部署。

利益相关：本仓查阅/运维、go_ai_talk 配置、OpenClaw Gateway 宿主。

## Goals / Non-Goals

**Goals:**

- Python 主路径只剩 tools + 知识库 + Intent/Clinic 飞轮实现。
- 三 agent workspace（intent/clinic/care_alert）可被 `openclaw.json5` 挂载；规则适配 tool-calling，不照搬 JSON 信封 prompt。
- README：LangGraph→OpenClaw 部署对照 + 最短命令。
- Go：审计确认已切新上游；删死客户端；配置/compose 对齐 Gateway。

**Non-Goals:**

- 不恢复 tip；不做 Care 飞轮。
- 不写云主机从零入门长文。
- 不把旧 classify 整段 JSON schema 复制进 AGENTS.md。
- 不生成测试文件。
- 不在本 change 强制收版 archive（可另做）。

## Decisions

### D1：Care 算卡只在 Gateway skill

- **选择**：删 Python `generate_care_alerts` 链；skill 调 history 只读 tools → 推理 → `emit_care_cards`；Go 已解析 tool_calls/items。
- **替代**：保留 Python analyze 供 Gateway HTTP 调 → 多一跳且违背「算力在 Gateway」。
- **原因**：用户明确 Care 算力完全交给 Gateway。

### D2：Intent skill = 原则 + tools，不是 JSON 分类器

- **选择**：从旧 prompt 提取「禁止编造 id / 叶子可写 / 读史 top_k / 低置信只问不写」写入 AGENTS/skills；写库走 history_* tools；回复 NL。
- **替代**：把 `intent_classification` 系统提示原样塞进 workspace → 与「废结构化信封」冲突，且撑爆 bootstrap 字数。
- **原因**：适配 OpenClaw tool loop。

### D3：删除顺序 = skill 先落地再删图

- **选择**：先写 workspaces 与 README 骨架，再删 `graphs/nodes`、`intent_pipeline`、Care 算卡；飞轮仍依赖的 `intent_cache_store` / `qa_fast_path` / `suggestion_acceptance` 保留。
- **替代**：先删后写 skill → 窗口期无规则可跑。
- **原因**：降低空窗风险。

### D4：README 短对照

- **选择**：对照表（旧只起 Python vs 新 Gateway+tools+Go）+ 编号最短步骤 + 2～3 条 curl；`docs/deploy-guide.md` 顶头标注过期或指向 README。
- **替代**：完整云主机教程 → 累赘。
- **原因**：用户已会 LangGraph 部署，只需迁移差。

### D5：Go 收尾范围

- **选择**：产品路径已用 `OpenClawHTTPClient`（审计写入 tasks 结论）；删除无调用方的 `PythonAIClient` 编排 API 或整文件中编排方法；manifest/compose 增加 `OPENCLAW_GATEWAY_URL`/`TOKEN`，弱化 `PYTHON_AI_TALK_URL` 作为编排暗示（若仍需给运维备忘，注释标明仅非编排遗留）。
- **替代**：留死客户端「以防万一」→ 继续误导。
- **原因**：与新 Python 面一致。

## Risks / Trade-offs

- **[Care 无 Python 硬闸]** skill 未强制 emit → 空卡 → Mitigation：AGENTS 强制最后调用 emit_care_cards；Go 已有空 items 处理。
- **[Intent 事件表过大]** 勿整表注入 AGENTS → Mitigation：先 `history_options` tool。
- **[误删飞轮依赖]** → Mitigation：tasks 列保留清单；删前 grep 引用。
- **[Go 配置缺 openclaw 键]** 仅靠环境变量 → Mitigation：补 manifest/示例配置。

## Migration Plan

1. 写入三 workspace + 更新 `openclaw.json5` 路径。
2. 重写 README 对照段。
3. 删 Care 算卡/飞轮与空壳；删 Intent/Clinic 无入口图与 pipeline。
4. Go 删死客户端 + compose 对齐。
5. 更新 `openspec/project.md` 目录表述（Care 无 Python 生成节点）。
6. 回滚：git revert；Gateway workspace 可单独回退。

## Open Questions

- Clinic workspace 首版 skill 粒度：单 AGENTS 还是拆「隐式采纳 / 陪伴回答」两个 skill（默认：**单 AGENTS + 短 skills 可选**）。
- `PythonAIClient` 是否整文件删除，或仅保留已被其他包引用的 DTO（默认：**voice 包内无调用方则删除编排方法；CareAlertAnalyzeItem 等若仍被 care_alert_service 使用则迁到独立 types 文件**）。

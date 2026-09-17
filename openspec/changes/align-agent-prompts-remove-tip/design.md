## Context

Flutter 已砍 tip；`d:\work\go_ai_talk` 中 change `remove-tip-and-clinic-feedback` 已完成，runtime `.go` 已无 `TipStream`/`/device/tip` 等入口。Python 仍暴露 tip 图与 `/v1/tip/stream`。care_alert 飞轮已拆，但 system 仍经 `prompt.json` 外置加载。各 agent 提示词文件布局不统一，reasoning 语言未全局约束；`openspec/project.md` 缺少 LLM agent/流式强制条款。

## Goals / Non-Goals

**Goals:**

- 删除 Python tip；Go 再 grep 确认无 tip，有残留则清，保障 clinic/care-alert/intent。
- care_alert system 内联（当前 `prompt.json` 文案）+ 中文思考；去掉外置文件/卷依赖。
- 每存活模块强制 `prompts/system.py`；shared 覆盖 needs_history / data_requirement。
- 对外 SSE 主 LLM 必须 `stream`；约定写入 project.md / AGENTS.md。

**Non-Goals:**

- 不恢复 tip 产品线；不改意图 CRUD 业务规则；不恢复通识/Q&A。
- 不要求内部判定节点（classify 等）改为 stream。
- 不在本变更收版全部历史 openspec tip 基线条文以外的无关 capability（tip 相关用 REMOVED）。

## Decisions

1. **单 change 一锅完成**  
   tip 删除 + 提示词对齐 + 全局文档 + Go 校对同批落地，避免半截状态。

2. **Go：先校对再删**  
   - 当前校对：`internal` 下无 tip 文件、无 TipStream 引用。  
   - Apply 时再全仓 grep；仅清理残留或文档。Python `scripts/patch_go_*` tip 片段删除或标注废弃。

3. **care_alert 文案来源**  
   - 以 `data/care_alert/prompt.json` 的 `output_format` 迁入 `CARE_ALERT_SYSTEM_PROMPT`。  
   - 删除 `prompt_store` 读写链路与仓库内 `prompt.json`；settings 去掉 `care_alert_prompt_dir`；compose 可去掉 care_alert 卷（若仅服务 prompt）。

4. **system.py 强制布局**  
   ```
   <module>/graphs/nodes/prompts/system.py  → XXX_SYSTEM_PROMPT
   ```  
   shared 可用同一文件内多个常量（`NEEDS_HISTORY_SYSTEM_PROMPT`、`DATA_REQUIREMENT_SYSTEM_PROMPT`）。统一句：`内部思考（reasoning）须使用中文。`

5. **流式真流式**  
   - 对外：`/v1/clinic/stream`、care-alert `/analyze/stream`、growth-trajectory turn、intent stream 等 → 主回答 MUST `llm_client.stream`。  
   - 对内：`invoke` 允许。  
   - 同步 `/v1/clinic` 可继续 invoke（非 SSE）。

6. **全局约束落点**  
   - 权威：`openspec/project.md` 新增「LLM Agent 提示词与流式约定」。  
   - 摘要：`AGENTS.md`。  
   - 同步删掉 project.md 中过时 tip/通识向量必建表述。

## Risks / Trade-offs

- [Python 删 tip 后若 Go 旧镜像仍调 `/v1/tip/stream` → 404] → Go 已无 tip；部署顺序先 Go 后 Python 或同时发。  
- [内联 prompt 后改文案需发版] → 已接受（对齐轨迹）。  
- [迁入口径与代码旧 default_output_format 不一致] → 强制以当前 prompt.json 为准，勿用短 default。  
- [shared system 拆分过度] → 单文件多常量即可。

## Migration Plan

1. Go grep 确认 → 无 tip 或清残留。  
2. Python 删 tip → 内联 care_alert → 抽各 system.py → 审计 stream → 写 project.md。  
3. 回滚：恢复 tip 模块与 prompt.json（git）；Go 若未改则无操作。

## Open Questions

- 无（explore 已确认；Go 路径已给）。

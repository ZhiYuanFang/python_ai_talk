## Why

Intent 的 `suggest` / `conversation` 已统一走 `call_clinic_agent` → `generate_clinic_answer`（`clinic_answer`）。`generate_response` 内对 `target_type == "suggest"` 的分支及整个 `suggest_answer.py` 在图上无入口，属于死代码，易误导后续改提示词的人以为建议仍走旧路径。应删除以收敛心智模型。

## What Changes

- 删除 `app/clinic/graphs/nodes/prompts/suggest_answer.py`
- 精简 `generate_response`：仅保留 history 回答路径（`history_answer`）；去掉 suggest 分支与相关 import
- **不删** `generate_response` 节点本身（intent history 短链仍依赖）
- 无 API **BREAKING**（行为不变：suggest 本就不走该分支）

## Capabilities

### New Capabilities

- `dead-suggest-path-removal`: 移除不可达的 suggest 同步生成提示词与分支，明确 generate_response 仅服务 history

### Modified Capabilities

- （无主库基线）

## Impact

- **代码**：`suggest_answer.py`（删除）、`generate_response.py`（瘦身）
- **运行时**：无行为变化；建议/闲聊仍走 clinic agent
- **文档**：若部署文档仍写「suggest → generate_response」，可顺带改正（非必须）

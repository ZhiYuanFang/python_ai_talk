## Why

整段「问+答」若绑定本机喂养史或陪伴对话私货，跨用户/跨阶段几乎不可复用；但若完全不做问答飞轮，又无法用「跳过生成 LLM」衡量越用越快。现有 `qa-fast-path` 在 hit 侧已挡点查/强制拉史，但 **promote 不看是否用过史**，且 **rejected 不禁捷径**，幻觉答被否认后仍可能再次命中同一条缓存。同时 clinic 生成提示词在 `needs_history=false` 时仍要求「有据必点名」，与无史可复用目标冲突。

## What Changes

- **写侧**：仅当上轮 `needs_history=false`（未以喂养史接地）且隐式 `accepted`、存在成功独立问句改写时，才将 Q→A 写入全局问答库；改写整理问句的行为保持不变。
- **读侧**：隐式语义判定前置；仅当本轮对上条建议 **非 `rejected`** 时才允许 Q&A 向量匹配捷径；高置信命中则直接返回答案（跳过 clinic 生成 LLM）。`rejected` 时置禁捷径并走完整生成，便于纠正幻觉。
- **捷径答被拒**：若上轮答案来自 Q&A 命中，拒绝时 MUST 下调该条问答质量分（避免脏条目继续服务其他用户）。
- 生成提示词分叉（口径 B）：`needs_history=true` 时保留「必须点名喂养记录」约束；`needs_history=false` 时 **不得** 要求点名喂养记录，也 **不得** 要求点名近期陪伴对话；无史路径产出可全局复用的通识/闺蜜口语答，且收尾 **SHALL** 轻轻引导家长肯定/否定这段回应（便于隐式采纳飞轮）。
- **会话元数据**：`last_suggestion` 持久化本轮是否史接地、以及（若适用）命中的 `qa_id`，供下一轮 promote / 拒答降分使用。
- tip 开场提示词与 tip 不进 Q&A 推广的既有行为 **不在本变更范围**（除非为实现共享字段所必需的序列化兼容）。

## Capabilities

### New Capabilities

- （无）

### Modified Capabilities

- `qa-fast-path`: 收紧 promote 条件（无史接地）；读侧 `rejected` 禁捷径；捷径答拒绝时降问答质量分。
- `implicit-suggestion-feedback`: 三态判定结果须驱动本轮是否允许 Q&A 捷径；rejected 时写出禁捷径信号。
- `needs-history-gate`: 与 clinic 生成提示词分叉对齐——门禁结果决定是否注入「点名史/对话」约束（无史路径关闭对话点名，口径 B）。
- `bestie-companion-persona`: clinic 生成在 `needs_history=false` 时 SHALL NOT 要求点名喂养记录或陪伴对话；`needs_history=true` 时保留有据点名。
- `companion-session`: `last_suggestion` 增加史接地与可选 `qa_match_id` 等字段以支持写/拒闭环。

## Impact

- 代码：`app/shared/qa_fast_path.py`、`suggestion_acceptance.py`、`companion_session.py`；`app/clinic/graphs/clinic_graph.py` 与相关节点；`app/clinic/graphs/nodes/prompts/clinic_answer.py`；`app/api/routes/clinic.py`（写会话字段）；`app/shared/vector_store.py`（问答质量更新，若尚无对 qa collection 的反馈 API）。
- API：对外 HTTP 契约不变；用户可见行为变化为——无史答不再被逼点名记录/对话；否认上条后本轮不再走问答捷径。
- 依赖：沿用既有 Chroma `qa_fast_path` 集合与隐式采纳判定；无新外部服务。

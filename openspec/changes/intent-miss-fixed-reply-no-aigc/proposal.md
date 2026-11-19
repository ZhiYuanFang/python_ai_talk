## Why

意图路径在 CRUD 以外命中 miss 时，会经 `soft_reply_for_miss` 用 LLM 生成对外软回复，使意图智能体出口带 AIGC 属性，触发合规申报成本。产品要求该兜底改为固定话术，本轮**仅**收窄 miss 软回复，不改查史/预测其它 LLM 成文路径。

## What Changes

- **BREAKING（对外文案）**：miss 终局对外 `content` 不再调用 LLM 软回复；固定为「我只能回答信息记录相关问题」。
- miss inbox / `fail_kind` / barge-in miss 判定仍基于**规范硬失败文案**（落库在替换对外文案之前），行为不变。
- 可删除或停用 `agent_miss_soft_reply` 的 LLM 调用与相关 system 提示（实现阶段清理死代码）。
- **非目标**：不改 `speak_predict` / `speak_history` 冷路径 LLM；不改 CRUD、确认/消歧模板；不关内部分类/段维 LLM。

## Capabilities

### New Capabilities

- （无）

### Modified Capabilities

- `agent-miss-adaptive-reply`：取消「LLM 自适应软回复」；改为固定非 AIGC 话术；保留「硬文案先落库」与 miss 定位语义。

## Impact

- `app/api/routes/intent.py`（miss 挂钩后写 `content`）
- `app/feeding/services/agent_miss_soft_reply.py`（及 `AGENT_MISS_SOFT_REPLY_SYSTEM_PROMPT`）
- 基线相对 `openspec/specs/v0.0.7.md` 中 `agent-miss-adaptive-reply`

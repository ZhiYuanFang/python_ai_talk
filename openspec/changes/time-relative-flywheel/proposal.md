## Why

段级 TIME 维当前「规则 → TIME LLM → rule_gap」、禁止向量飞轮；半命中口语（如「昨晚八点」）每次冷路径都打 TIME LLM。其它维已整段飞轮加速，唯时间因绝对 Unix 跨天会错被禁用。探索已定：**纯 A——只缓存相对时间配方，命中时用当前 Asia/Shanghai 物化**，从而跨天同句可跳过 TIME LLM，且不引入毒缓存。

## What Changes

- **BREAKING（契约）**：撤销「时间维禁止向量飞轮」；改为允许 `feeding_time_cues`，payload 仅为相对配方，**禁止**以 `start_time`/`end_time` Unix 作为主缓存。
- 新增时间整段飞轮：规则 miss 后检索配方 → 物化；miss 再 TIME LLM；仅当 LLM 产出合法配方才整段回写。
- TIME LLM 契约改为**主出相对配方**（可附带当次物化 unix 供落库）；仅有 unix、无合法配方时当次可落库但 **MUST NOT** 回写飞轮。
- **不做**同日绝对 Unix TTL 兜底。
- `read`（record|predict）跳过 TIME 飞轮读写；规则已完整抽出时可不读飞轮。
- 保留 `dimension=time` 的 rule_gap（飞轮加速热路径，缺口仍驱动扩规则）。
- Admin：`/v1/admin/time-cache`（list/bulk/delete）；Hub 页可选兄弟仓。

## Capabilities

### New Capabilities

- `intent-time-relative-flywheel`：相对配方 TIME 飞轮、物化、LLM 契约、读路径跳过、禁绝对 Unix 主缓存

### Modified Capabilities

- `intent-flywheel-layers`：时间层纳入分层飞轮清单；删除「时间禁飞轮」
- `intent-dim-resolve`：时间维改为规则 → 飞轮 → LLM → 配方回写（与统一 `resolve_*` 形状对齐）
- `intent-rule-gap-inbox`：时间仍写缺口；不再以「禁飞轮」为由否定时间向量加速

## Impact

- Python：`time_cue_store`、`materialize`、`dim_resolve.resolve_time`、`segment_multidim` TIME 段、`SEGMENT_TIME_LLM_PROMPT` / `llm_resolve_time`、admin 路由
- OpenSpec：改写既有「时间禁飞轮」Requirement
- 存量：无合法绝对 Unix 旧库（本维新建）；Hub 可选
- Go：无强制

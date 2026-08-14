## Why

`invoke` 保底换模把一次上游失败拉成串行多提供商尝试，用户侧表现为超时，几乎无收益。选型（含 VIP）已由 Go 决定；Python 应只打请求给定的唯一 model，失败立即结束并给出明确文案。

## What Changes

- **BREAKING**：删除 `llm_client.invoke` 跨 `(provider, name)` 保底切换；不再读取 `LLM_FALLBACK_MODELS` 作为候选序。
- **BREAKING**：`invoke` / 业务入口缺合法 `model` 时直接失败，**无** Python 默认单模、**无**纯保底序。
- `invoke` 与 `stream` 对齐为「单次、唯一 model」；失败向上抛出或由业务层转为用户可见「脑电波过载，请稍后重试」。
- 保留既有非换模机制：Redis 并发闸门等待、兄弟仓 HTTP 重试、业务级默认（如 data_requirement fallback）。**不**新增同模 LLM N 次重试。
- Python **不**根据 VIP/会员选模；是否传 model 完全由 Go 负责。
- 意图分类等软失败文案统一为「脑电波过载，请稍后重试」（可同步 thinking 一条，有 writer 时）。
- 清理 settings / env 中保底列表配置与「缺省走保底」注释口径。

## Capabilities

### New Capabilities

- （无）

### Modified Capabilities

- `llm-fallback-chain`：废除 invoke 保底换模与「无 model 走保底序」；改为单模必传、失败即止；保留「Python 无 VIP 逻辑」；stream 单模要求不变并与 invoke 对齐。
- `langgraph-intent-graph`（或意图失败路径相关要求）：分类 LLM 失败时用户可见文案改为「脑电波过载，请稍后重试」。

## Impact

- **代码**：`app/shared/llm_client.py`、`settings`、env 模板；intent / care_alert / clinic 路由与 schema 中「可选 model → 保底」口径；`classify_intent`（及同类软失败）文案。
- **调用方（Go）**：intent / care_alert 须始终传入可用 model（与 clinic/tip 一致）；省略不再由 Python 兜底。
- **运维**：`LLM_FALLBACK_MODELS` 失效可删除；硅基/魔搭等 provider 接入可保留供 Go 选型。
- **非目标**：不改 VIP 业务规则（仍在 Go）；不写测试文件。

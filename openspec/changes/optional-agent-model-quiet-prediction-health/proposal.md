## Why

Go 侧智能体入口将不再传入 `model`，本仓 intent / clinic / care-alert 请求体仍把 `model` 标为必填，入站即 `Field required`，请求进不了图；而 `llm_client` 临时阶段已硬编码 runtime 且可接受 `None`。同时 `python-prediction` 未过滤 `/v1/health` 的 uvicorn access 日志，Docker healthcheck 周期性刷屏。

## What Changes

- **智能体 HTTP 契约**：intent、clinic、care-alert（及同口径其它 LLM 入口）的 `model` 改为**可选**；缺省 MUST NOT 再因校验失败拒绝；有传则仍可入 state/日志，实际上游选型仍由 `llm_client` TEMPORARY runtime 决定（不恢复保底换模链）。
- **下游解析**：路由与 `resolve_model_config` 等 MUST 容忍 `model` 缺省，不得在缺省时二次抛「必传」。
- **prediction 健康检查日志**：`prediction.main` MUST 与 talk 一样过滤 `uvicorn.access` 中含 `/v1/health` 的记录。
- **非目标**：不改 Go；不删除 TEMPORARY runtime 硬编码；不恢复 `LLM_FALLBACK_MODELS` 换模；不改 health 响应体。

## Capabilities

### New Capabilities

- （无）

### Modified Capabilities

- `llm-fallback-chain`：撤销「HTTP 契约 model 必填 / 缺省即失败」；改为可选，缺省走临时 runtime，仍禁止保底换模链。
- `llm-runtime-model-override`：明确请求可省略 `model`；缺省时仍用硬编码 runtime，并保留可观测日志。
- `access-log-filter`：过滤范围覆盖 `prediction.main` 入口（不仅 `app.main`）。

## Impact

- Schema：`app/feeding/schemas/intent.py`（Intent / Clinic）、`app/care_alert/schemas/care_alert.py`；路由 `intent.py` / `clinic.py` / `care_alert.py`；`care_alert/services/model_resolve.py`。
- 日志：`prediction/main.py`（对齐 `app/main.py` 的 health access filter）。
- 基线：相对 `openspec/specs/v0.0.7.md` 中 Required model 与 access-log-filter 表述。

## Why

产品验证阶段 Go 侧传入的 model 不稳定（弱模/错模），导致各业务线行为不一致；路由层已出现多处散落「写死 model」且互不一致（intent 硅基、care-alert/growth deepseek）。需要在 Python 侧用**临时、全站统一**的强制选型压住噪声，等产品验证后再恢复 Go 选型适配。

## What Changes

- 在 `llm_client._require_model_config` 内**常量硬编码** runtime model（`deepseek` / `deepseek-v4-flash` / `max_in_flight=50`），`invoke` / `stream` 一律使用该配置，**忽略**调用方传入的 Go model。
- **不**新增 env 变量、**不**恢复 fallback 换模链、**不**改 HTTP 契约（Go 仍可传 `model`，仅被忽略）。
- 删除路由层已有散写死（intent / care-alert stream / growth-trajectory 等），避免双源覆盖。
- 覆盖生效时打 INFO 日志，标明忽略了 Go 传入值。
- 本变更为**临时方案**：产品验证后删除硬编码，恢复尊重 Go 传入。

## Capabilities

### New Capabilities

- `llm-runtime-model-override`: 临时强制 runtime 模型选型（常量硬编码于 llm_client，全站 invoke/stream 生效）

### Modified Capabilities

- （无）既有「按请求 model 调用」的场景仍可作为契约保留；行为偏差由新 capability 明确覆盖为临时强制选型。

## Impact

- 代码：`app/shared/llm_client.py`（`_require_model_config`）；清理 `app/api/routes/intent.py`、`care_alert.py`、`growth_trajectory.py` 等路由散写死。
- API：请求/响应 schema 不变；实际上游模型与 Go 传入脱钩。
- 运维：换临时型号需改代码发版（刻意选择，不做 env）。
- 依赖：无新依赖；须保证 `DEEPSEEK_API_KEY` 可用。

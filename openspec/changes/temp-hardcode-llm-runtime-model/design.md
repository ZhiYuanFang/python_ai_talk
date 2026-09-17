## Context

当前契约是「Go 选型、Python 不换模」：`llm_client.invoke` / `stream` 经 `_require_model_config` 校验后原样使用传入的 `LLMModelConfig`。产品验证阶段 Go 传入不稳定，路由层已出现互不一致的散写死（intent→硅基 Qwen；care-alert stream / growth-trajectory→deepseek-v4-flash；clinic / care-alert 非流仍跟 Go）。需要临时全站统一强制型号，且不引入 env。

## Goals / Non-Goals

**Goals:**

- 在 `_require_model_config` 一处常量硬编码 runtime model，覆盖所有经 `llm_client` 的调用。
- 忽略 Go / 路由传入的 provider/name/max_in_flight。
- 清理路由散写死，单一真相源。
- 覆盖时 INFO 可观测；中文注释标明 TEMPORARY。

**Non-Goals:**

- 不新增 `LLM_RUNTIME_*` 等 env / settings 字段。
- 不恢复 `LLM_FALLBACK_MODELS` 或多候选换模。
- 不修改 HTTP 请求 schema（`model` 仍可必填/可选如旧）。
- 不修复 growth-trajectory「一直提问」的图逻辑（仅排除模型噪声）。
- 不做 per-product-line 分套型号。

## Decisions

### D1: 落点选 `_require_model_config`，而非各路由

- **选择**：`invoke`/`stream` 共用的 `_require_model_config` 返回硬编码 `LLMModelConfig`。
- **理由**：全仓 LLM 调用均经此入口；无漏口；回滚改一处。
- **备选**：路由覆盖 — 已证明易漏且型号分裂；middleware — 过重。

### D2: 常量硬编码，不读 env

- **选择**：模块级常量（或 `_require_model_config` 内字面量）：
  - `provider = "deepseek"`
  - `name = "deepseek-v4-flash"`
  - `max_in_flight = 50`
- **理由**：用户明确选 A；与 care-alert/growth 现用一致；临时方案避免配置面膨胀。
- **备选**：settings/env — 换模免发版，但本期不做。

### D3: 传入 model 非 None 时仍覆盖（而非「缺省才用硬编码」）

- **选择**：无论传入为何，一律返回硬编码；若传入与硬编码不同则 INFO 记录「忽略 Go model」。
- **理由**：临时方案目标是强制统一，不是兜底。
- **备选**：仅缺省时填充 — 无法压住错误 Go 选型。

### D4: 清理路由散写死

- **选择**：删除 `intent._model_config_dict`、`care_alert` stream、`growth_trajectory` 中的本地写死；恢复从 request 取 model 写入 state（值随后仍被 client 忽略）。
- **理由**：避免双层覆盖；日志与契约可读。

### D5: 临时生命周期

- **选择**：代码注释与本 change 文档标明 TEMPORARY；产品验证后删除硬编码并恢复 `_require_model_config` 尊重传入。
- **理由**：不引入 override 开关（用户不要 env；开关亦非必须）。

## Risks / Trade-offs

- [换模需发版] → 可接受；临时；注释写清常量位置。
- [DeepSeek key 缺失则全站失败] → 与强制 deepseek 一致；部署前确认 `DEEPSEEK_API_KEY`。
- [路由日志仍显示 Go model] → client 层 INFO 标明实际 runtime；可选后续统一日志（本期不强制）。
- [掩盖 Go 选型 bug] → 刻意；验证后再打磨 Go 适配。
- [与历史「Python 不换模」叙事冲突] → 新 capability 明确为临时覆盖；归档时若仍临时则写入基线并标注。

## Migration Plan

1. 实现硬编码 + 清理路由散写死。
2. 部署后手工：任意接口（intent/clinic/care-alert/growth）打 LLM，日志见 runtime=`deepseek`/`deepseek-v4-flash`，且与 Go 传入不同时有「忽略」日志。
3. 回滚：还原 `_require_model_config` 原逻辑（git revert 本 change）。

## Open Questions

- （无）硬编码三元组与「不写 env」已由用户确认。

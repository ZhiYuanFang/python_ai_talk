## Context

- Go 将停止在智能体 HTTP 体里传 `model`；本仓 Pydantic 仍必填 → `Field required`。
- `llm_client._require_model_config` 已 TEMPORARY 硬编码 runtime，且文档写明传入可为 `None`；缺口在入站 schema 与 `resolve_model_config`。
- growth-trajectory 请求已 Optional；intent / clinic / care-alert 仍必填。
- talk 的 `app.main` 已过滤 `/v1/health` access log；`prediction.main` 未过滤，healthcheck 刷屏。

## Goals / Non-Goals

**Goals:**

- 无 `model` 时各智能体入口校验通过并可跑通到 LLM。
- 有 `model` 时行为与今日兼容（写入 state/日志；上游仍被 TEMPORARY 覆盖）。
- 禁止恢复保底换模链。
- prediction 健康检查不再刷 access 日志。

**Non-Goals:**

- 不改 Go 客户端。
- 不移除 TEMPORARY runtime 常量（另案收尾）。
- 不改 health 响应 JSON、不改 healthcheck 间隔。
- 不恢复 tip 产品线。

## Decisions

1. **`model` 可选，缺省 `None`**  
   - Intent / Clinic：`Optional[ModelConfig] = None`。  
   - Care-alert：`Optional[...]`，`_normalize_model_field` 对 `None` 原样放行（或跳过校验）。  
   - growth-trajectory 保持 Optional。  
   - 备选：入站注入假 ModelConfig → 易误导日志「Go 传了型号」，否决。

2. **路由缺省安全**  
   - 构建 `llm_model` dict 时：`request.model is None` → `{}` 或省略；禁止 `.provider` 裸访问。  
   - `resolve_model_config(None)` → 返回空占位 dict（或与 override 一致的占位），MUST NOT raise「必传」；真正选型仍在 `llm_client`。

3. **TEMPORARY 仍是上游唯一权威**  
   - 与既有 `llm-runtime-model-override` 一致；本变更只打通「无 model 也能进 invoke/stream」。  
   - 缺省时 `_require_model_config(None)` 已有「调用方未传 model」INFO 日志，保持。

4. **prediction access filter**  
   - 在 `prediction/main.py` 对 `uvicorn.access` 挂与 talk 同语义的 Filter（消息含 `/v1/health` 则丢弃）。  
   - 模块 import 即生效，覆盖 `uvicorn prediction.main:app`。

5. **基线**  
   - MODIFIED：`llm-fallback-chain` 的 Required model 两条改为可选；`llm-runtime-model-override` 补「可省略」；`access-log-filter` 的入口覆盖 prediction。

## Risks / Trade-offs

- [基线「Go MUST 传 model」被改写] → 与产品现状一致；TEMPORARY 结束后若恢复尊重调用方，须另案决定缺省策略。  
- [路由漏改导致 AttributeError] → tasks 明确扫 intent/clinic/care-alert。  
- [过滤过宽误伤业务日志] → 仅匹配 `/v1/health` 子串，与 talk 一致。

## Migration Plan

1. 部署本仓 talk + prediction 镜像。  
2. Go 可停传 `model`；旧包仍传也不坏。  
3. 回滚：恢复必填会再次拒绝无 model 请求，不宜在 Go 已停传后回滚 schema。

## Open Questions

- （无）临时 runtime 具体型号以代码常量为准；本变更不纠偏基线里旧 deepseek-v4-flash 字面（可另案）。

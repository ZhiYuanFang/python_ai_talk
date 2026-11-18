## 1. 请求契约：model 可选

- [x] 1.1 Intent / Clinic 请求 schema：`model` 改为 `Optional[ModelConfig] = None`；注释标明 Go 可省略
- [x] 1.2 Care-alert 请求：`model` 可选；`_normalize_model_field` 对 None 放行（不抛必传）
- [x] 1.3 确认 growth-trajectory 已 Optional；注释与三仓口径一致

## 2. 路由与解析容忍缺省

- [x] 2.1 intent / clinic 路由：`request.model is None` 时安全构建 `llm_model`（空 dict），禁止裸访问 `.provider`
- [x] 2.2 `resolve_model_config(None)`：不抛「必传」，返回空/占位 dict，交由 `llm_client` TEMPORARY runtime
- [x] 2.3 care-alert / growth 日志路径在 model 缺省时不崩溃

## 3. prediction 健康检查日志

- [x] 3.1 `prediction/main.py`：为 `uvicorn.access` 安装与 talk 同语义的 `/v1/health` 过滤 Filter（中文注释）

## 4. 验收

- [x] 4.1 手工：无 model 调 intent/clinic/care-alert 不再 `Field required`；有 model 仍可入站
- [x] 4.2 手工：prediction 连续 `/v1/health` 不刷 access 日志，且仍返回 healthy

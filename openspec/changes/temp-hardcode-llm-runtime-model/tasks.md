## 1. llm_client 硬编码

- [x] 1.1 在 `app/shared/llm_client.py` 增加 TEMPORARY 常量（`deepseek` / `deepseek-v4-flash` / `max_in_flight=50`），中文注释标明产品验证临时方案、验证后删除
- [x] 1.2 改写 `_require_model_config`：一律返回硬编码配置；传入与硬编码不一致时 INFO 记录忽略 Go/调用方 model；保留 provider 规范化与缺字段时的安全处理（硬编码自身完整则不再依赖传入）
- [x] 1.3 更新模块/方法中文注释：临时强制选型，不读 env、不恢复 fallback

## 2. 清理路由散写死

- [x] 2.1 `app/api/routes/intent.py`：恢复 `_model_config_dict` 从 `request.model` 取值（去掉硅基硬编码）
- [x] 2.2 `app/api/routes/care_alert.py`：删除 stream（及若存在的 analyze）对 `request.model` 的本地写死
- [x] 2.3 `app/api/routes/growth_trajectory.py`：删除对 `request.model` 的本地写死
- [x] 2.4 确认 `clinic` 等其它路由无新增散写死；无需改逻辑时仅核对

## 3. 手工验收

- [x] 3.1 任选 intent / clinic / care-alert / growth-trajectory 之一发起真实 LLM 调用，确认日志实际 provider/name 为 deepseek / deepseek-v4-flash
- [x] 3.2 请求故意传不同 model，确认出现「忽略」类 INFO，且上游仍为硬编码型号

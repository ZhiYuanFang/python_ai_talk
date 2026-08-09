## 1. 配置与提供商

- [x] 1.1 `settings` 增加 siliconflow / modelscope 的 api_key、base_url 默认值，以及 `llm_fallback_models`（字符串或解析列表）
- [x] 1.2 `normalize_llm_provider` / `_get_client` 支持 `siliconflow`、`modelscope`；更新「未知提供商」拒绝逻辑；中文注释
- [x] 1.3 `env/.env.prod` / `.env.test` / compose 增加 key/base_url 与 `LLM_FALLBACK_MODELS`（含 glm + 硅基 + 魔搭默认可调序）；中文备注标明仅非流式保底

## 2. 保底链（invoke）

- [x] 2.1 实现候选序列：有 primary → primary + 保底；无 primary → 仅保底；去重、跳过空 key
- [x] 2.2 实现可恢复错误判定（429/5xx/超时/连接/型号不可用）；内容类 400 不切换
- [x] 2.3 `invoke`：按候选依次尝试，成功即返回；切换打 WARN 日志；全失败上抛
- [x] 2.4 `stream`：不走保底；仅使用传入 model；缺 model 抛错；失败直接上抛

## 3. model 契约

- [x] 3.1 intent / care_alert：`model` Optional；空 → invoke 纯保底
- [x] 3.2 clinic / tip：`model` 必填（Go 流式必带）；路由注入完整 model_config
- [x] 3.3 节点统一 `llm_model_config_from_mapping`，去掉硬编码 deepseek 默认

## 4. 校验

- [x] 4.1 `openspec validate llm-fallback-chain --strict` 通过

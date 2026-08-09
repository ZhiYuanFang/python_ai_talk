## 1. 配置与提供商

- [x] 1.1 `settings` 增加 siliconflow / modelscope 的 api_key、base_url 默认值，以及 `llm_fallback_models`（字符串或解析列表）
- [x] 1.2 `normalize_llm_provider` / `_get_client` 支持 `siliconflow`、`modelscope`；更新「未知提供商」拒绝逻辑；中文注释
- [x] 1.3 `env/.env.prod`（及若有本地 env 示例）增加空 key/base_url 与 `LLM_FALLBACK_MODELS`，中文备注标明硅基流动 / 魔搭；GLM/DeepSeek 行补充免费档与付费不进保底说明

## 2. 保底链（全仓）

- [x] 2.1 实现候选序列：primary → 解析保底列表，去重、跳过空 key
- [x] 2.2 实现可恢复错误判定（429/5xx/超时/连接）；400 类不切换
- [x] 2.3 `invoke`：按候选依次尝试，成功即返回；切换打 WARN 日志；全失败上抛
- [x] 2.4 `stream`：首包前可换模重开流；已 yield 非空增量后不再换模

## 3. 校验

- [x] 3.1 `openspec validate llm-fallback-chain --strict` 通过

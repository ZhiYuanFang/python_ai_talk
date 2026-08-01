## 1. Provider 规范化

- [x] 1.1 在 `app/shared/llm_client.py` 增加 provider 规范化（strip + lower；`zhipu` → 内部 `glm`），并加中文业务注释
- [x] 1.2 修改 `_get_client`：用规范名选择 API Key/Base URL 与 cache key；`zhipu`/`glm` 共用智谱配置；未知 provider 仍报错

## 2. 文档对齐

- [x] 2.1 更新 `LLMModelConfig` 与 `ModelConfig`（intent schema）字段说明：可选值含 `deepseek`、`glm`、`zhipu`

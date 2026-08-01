## Why

生产请求传入 `provider: "zhipu"` 时，`LLMClient._get_client` 只认 `"glm"`，抛出 `ValueError: 不支持的 LLM 提供商: zhipu`。智谱与本仓 `GLM_*` 配置本是同一提供商，调用方已用 `zhipu` 命名，需要在 Python 侧双收别名，避免强迫兄弟仓改契约。

## What Changes

- `LLMClient` 将 `zhipu` 与 `glm` 视为同一提供商，共用 `glm_api_key` / `glm_base_url`
- 规范化 provider（含大小写）后再选客户端与缓存 key，避免 `zhipu:` / `glm:` 各建一份缓存
- 更新 `LLMModelConfig` / 请求 schema 文档说明：可选值含 `deepseek`、`glm`、`zhipu`
- **不**改环境变量名（仍为 `GLM_API_KEY`）；**不**要求 Go 改传 `glm`

## Capabilities

### New Capabilities

- `llm-provider-alias`: LLM provider 名称别名与规范化（`zhipu`↔`glm`）

### Modified Capabilities

- （无：`openspec/specs/` 下无已归档基线）

## Impact

- **代码**：`app/shared/llm_client.py`；可选同步 `app/feeding/schemas/intent.py` 中 ModelConfig 描述
- **API**：请求体 `model.provider` 可传 `zhipu` 或 `glm`，行为等价
- **依赖 / 跨仓**：无新依赖；Go 可继续传 `zhipu`

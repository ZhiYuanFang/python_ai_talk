## Why

免费档上游（如智谱 Flash）易出现 429/超时，导致 care_alert、意图分类等非流式 LLM 调用直接失败。Go 负责 VIP 选付费首选；非 VIP 非流式可省略 model。Python 需按本地可调的**国内永久免费**保底链在 `invoke` 上依次尝试。流式 clinic/tip 型号能力不一，本期不做流式保底；由 Go 必带 model。

## What Changes

- 在共享 `llm_client.invoke` 实现保底：
  - **有 model** → 先打传入首选，可恢复失败后再按 `LLM_FALLBACK_MODELS` 依次尝试。
  - **无 model** → 仅按 `LLM_FALLBACK_MODELS` 顺序尝试。
- `llm_client.stream`：**不**走保底；仅打传入的唯一 model；缺 model 失败。
- 新增国内永久免费提供商（硅基流动、魔搭）；智谱可写入保底列表；默认不含付费 DeepSeek。
- HTTP：intent / care_alert 的 `model` 可选；clinic / tip 的 `model` 必填（Go 流式必带）。
- 保底列表与 key 由环境变量配置，注释标明仅非流式保底。

## Capabilities

### New Capabilities

- `llm-fallback-chain`: invoke 保底切换、stream 单模、可恢复错误判定、非流式可选 model、配置与观测。

### Modified Capabilities

- `llm-provider-alias`: 支持 siliconflow、modelscope 及对应 key/base_url 选路。

## Impact

- `app/shared/llm_client.py`、`app/config/settings.py`、`env/.env.*`、`docker-compose.yml`、相关 schemas/routes/节点。
- Go：流式（clinic/tip）必带 model；非流式非 VIP 可省略。
- 运维通过改 `LLM_FALLBACK_MODELS` 调整非流式免费顺序。

## Why

免费档上游（如智谱 Flash）易出现 429/超时，导致 care_alert、clinic、tip 等全仓 LLM 调用直接失败。Go 已负责选定请求首选模型；Python 需在首选失败后自动切换到本地配置的**国内永久免费**保底链，保证思考/生成流程尽量不中断。

## What Changes

- 在共享 `llm_client`（`invoke` / `stream`）实现全仓保底：先打请求传入的 model，可恢复失败后再按配置列表依次尝试。
- 新增国内永久免费提供商接入（硅基流动、魔搭 ModelScope），扩展 `_get_client` / settings；**不**把付费 DeepSeek 放进保底列表。
- 保底列表与 key/base_url 由环境变量配置；`.env.prod`（及本地示例）增加空 key 占位，中文备注标明哪家。
- Python **不**解析 VIP；VIP/付费首选由 Go 决定并传入 model。
- stream：仅在尚未向调用方产出内容前切换模型；已吐 token 后不再静默换模。

## Capabilities

### New Capabilities

- `llm-fallback-chain`: 全仓 LLM 首选失败后的国内永久免费保底切换、可恢复错误判定、配置与观测。

### Modified Capabilities

- `llm-provider-alias`: 在既有 deepseek/glm(zhipu) 之外，SHALL 支持保底所需的国内提供商别名（siliconflow、modelscope）及对应 key/base_url 选路。

## Impact

- `app/shared/llm_client.py`、`app/config/settings.py`、`env/.env.prod`（及若有的 env 示例）。
- 所有经 `llm_client` 的调用方自动受益（care_alert / clinic / tip / feeding 门禁与隐式反馈等），HTTP 契约不变。
- 运维需事后填入硅基流动、魔搭等 API Key；未配置的候选跳过。

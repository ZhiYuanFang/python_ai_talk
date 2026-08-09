## Context

`llm_client` 仅支持 deepseek / glm(zhipu)，`invoke`/`stream` 失败即上抛。生产日志显示非 VIP 路径常用 `glm-4.7-flash` 遇 429 导致 care_alert 等业务 500。Go 负责选首选模型（含 VIP）；Python 负责可用性保底。

## Goals / Non-Goals

**Goals:**

- 全仓：`llm_client.invoke` / `stream` 统一保底链。
- 首选 = 调用方传入的 `LLMModelConfig`；失败后按本地配置的国内永久免费列表依次试。
- 接入硅基流动、魔搭；env 占位 + 中文备注哪家；空 key 跳过。
- 可恢复错误才切换；stream 仅首包前切换。

**Non-Goals:**

- Python 不解析 VIP / 会员。
- 保底不包含付费 DeepSeek、不包含新人赠金型通道（百炼新人额度、月之暗面赠金等）。
- 不在此 change 改提示词长度或 care_alert 业务逻辑。
- 不自动生成测试。

## Decisions

### D1: 中枢落点

在 `LLMClient.invoke` / `stream` 内建「试候选序列」，调用方零改动。Redis `max_in_flight` 仍按**当前候选**的 model name 取闸。

### D2: 候选序列

1. primary = 入参 `model_config`  
2. 其后为 `settings.llm_fallback_models` 解析出的 `(provider, name)` 列表  
3. 跳过与 primary 相同的 `(provider, name)`（provider 经 normalize）  
4. 跳过：该 provider 的 api_key 为空；或构建 client 时明确不可用  

默认列表示例（可被 env 覆盖，型号以控制台当前永久免费为准）：

`siliconflow:Qwen/Qwen3-8B,siliconflow:THUDM/glm-4-9b-chat,modelscope:Qwen/Qwen2.5-7B-Instruct`

### D3: 可恢复失败

切换：HTTP 429、5xx、超时、连接错误、以及等价的 OpenAI/SDK 异常。  
不切换：明确的 400 类「请求内容/参数非法」（换模无益且掩盖 bug）。  
某候选因「未配置 key」：记日志并试下一个，不视为整链终结。

### D4: 新提供商（国内永久免费语义）

| provider | key / base_url settings | 默认 base_url |
|----------|-------------------------|---------------|
| `siliconflow` | `SILICONFLOW_API_KEY` / `SILICONFLOW_BASE_URL` | `https://api.siliconflow.cn/v1` |
| `modelscope` | `MODELSCOPE_API_KEY` / `MODELSCOPE_BASE_URL` | `https://api-inference.modelscope.cn/v1` |

智谱继续用现有 `GLM_*`；deepseek 仅作 Go 传入的付费首选，**默认不进** `LLM_FALLBACK_MODELS`。

### D5: stream 策略

在拿到第一个可向调用方 yield 的 content/thinking 之前失败 → 可换下一候选重开流。  
已 yield 过非空增量后失败 → 不再换模，按现网上抛（避免半截答案拼接错乱）。

### D6: 配置与 env 备注

- `LLM_FALLBACK_MODELS`：逗号分隔 `provider:model_name`（model 名可含 `/`）。  
- `.env.prod` 增加空 key 与 base_url，注释写明「硅基流动」「魔搭 ModelScope」；现有 GLM/DeepSeek 行补充「永久免费档 / 付费不进保底」类备注。

### Alternatives considered

- 仅 care_alert 保底 → 否决：用户要求全仓。  
- 保底含 deepseek → 否决：现网 deepseek 为付费。  
- 保底含百炼/月之暗面 → 否决：偏新人额度，非永久免费。

## Risks / Trade-offs

- [免费型号 ID 变更] → env 可改列表；默认 ID 在注释标明「以控制台为准」。  
- [魔搭日次耗尽仍 429] → 链上下一家；全挂则原错误上抛。  
- [同账号智谱多 Flash] → 默认保底不以智谱为主，避免 429 连坐。  
- [stream 半截失败] → 不静默换模，可能仍失败（接受）。  
- [延迟叠加] → 每次失败才切换；打 WARN 便于观测。

## Migration Plan

1. 部署代码；key 为空时行为≈仅多试空列表（等同只打 primary）。  
2. 运维填硅基/魔搭 key 后保底生效。  
3. 回滚：去掉保底逻辑或清空 `LLM_FALLBACK_MODELS`。

## Open Questions

- 无（型号以填 key 时控制台永久免费列表最终校准即可）。

## Context

`llm_client` 需支持多国内免费提供商与保底切换。生产曾出现：智谱 429、硅基型号下架、魔搭无效型号。Go 负责选模型；非 VIP 的非流式可省略 model，由 Python 按 env 保底序调用。流式（clinic/tip）由 Go 必带 model，Python 不换模。

## Goals / Non-Goals

**Goals:**

- **仅 `invoke`** 走保底链：有 primary → 首选 + 保底；无 primary → 仅保底（顺序=env 可调）。
- **`stream` 不保底**：只打调用方传入的唯一 model；失败直接上抛；未传 model 则失败。
- 保底可含智谱 Flash、硅基流动、魔搭；env 可调序。
- 非流式 HTTP（intent / care_alert）`model` 可选；clinic / tip（真 LLM stream）`model` 必填。
- 可恢复错误才在 invoke 上切换；型号不可用视为可切换。

**Non-Goals:**

- Python 不解析 VIP / 会员。
- 本期不做流式专用保底列表 / 流式换模。
- 保底默认不包含付费 DeepSeek、不包含新人赠金型通道。
- 不在此 change 改提示词长度或 care_alert 业务逻辑。
- 不自动生成测试。

## Decisions

### D1: 中枢落点

保底序列仅在 `LLMClient.invoke` 内构建。`stream` 单次 `_stream_once`，不做候选循环。Redis `max_in_flight` 按当前 model name 取闸。

### D2: invoke 候选序列

1. 若传入 primary → 先入队  
2. 其后为 `settings.llm_fallback_models` 解析出的 `(provider, name)`  
3. 与已入队项同 `(provider, name)` 则跳过  
4. 保底项：provider 未接入或 api_key 为空则跳过  
5. 最终无候选 → `ValueError`

### D3: 可恢复失败（仅 invoke）

切换：HTTP 429、401/403、5xx、超时、连接错误、型号不可用、本候选 API Key 未配置。  
不切换：其它明确 400「请求内容/参数非法」。

### D4: 新提供商

| provider | key / base_url settings | 默认 base_url |
|----------|-------------------------|---------------|
| `siliconflow` | `SILICONFLOW_API_KEY` / `SILICONFLOW_BASE_URL` | `https://api.siliconflow.cn/v1` |
| `modelscope` | `MODELSCOPE_API_KEY` / `MODELSCOPE_BASE_URL` | `https://api-inference.modelscope.cn/v1` |

智谱用 `GLM_*`，可写入保底列表。deepseek **默认不进** `LLM_FALLBACK_MODELS`。

### D5: stream 不保底 + Go 必带 model

- clinic / tip：Go **一律**传入完整 `model`（VIP 付费或非 VIP 自选免费流式型号）。  
- Python：`stream` 仅使用该 model；不读 `LLM_FALLBACK_MODELS`；失败不上保底。  
- 未传 / 无法解析 model → 明确错误（schema 必填 + `stream` 内校验）。  
- intent 的 HTTP `/stream` 图内 LLM 仍是 `invoke`，继续吃保底（与 clinic/tip token 流无关）。

### D6: 非流式可选 model

- Go：非流式非 VIP 可省略 model。  
- intent / care_alert：`model` Optional → 空配置 → invoke 纯保底序。

### D7: 配置

- `LLM_FALLBACK_MODELS`：逗号分隔 `provider:model_name`（仅影响 invoke）。  
- env / compose 中文备注标明「仅非流式保底」。

### Alternatives considered

- stream 首包前换模 → 否决：流式型号能力不一，本期不做。  
- 双列表 stream/invoke → 搁置；需要时再开。  
- 非 VIP 流式省略 model → 否决：与「stream 不保底」冲突；改为 Go 流式必带。

## Risks / Trade-offs

- [流式上游 429] → 无保底，直接失败（接受；由 Go 选型与重试策略负责）。  
- [免费型号 ID 变更] → env 改 invoke 列表即可。  
- [Go 未带 clinic/tip model] → 400，尽快暴露契约问题。

## Migration Plan

1. 部署 Python：invoke 保底；stream 单模。  
2. Go：clinic/tip 始终带 model；非流式非 VIP 可省略。  
3. 回滚：清空保底列表或回退代码。

## Open Questions

- 无。

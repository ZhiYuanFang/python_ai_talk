## ADDED Requirements

### Requirement: Accept siliconflow provider
系统 SHALL 将 LLM provider 值 `siliconflow`（规范化后）识别为硅基流动，并使用 `siliconflow_api_key` 与 `siliconflow_base_url`（缺省国内官方 OpenAI 兼容地址）创建客户端。

#### Scenario: Provider siliconflow with key
- **WHEN** 调用方或保底链使用 `provider=siliconflow` 且 SiliconFlow API Key 已配置
- **THEN** 系统 SHALL NOT 因提供商名称拒绝，并 SHALL 使用硅基流动 Base URL 发起调用

### Requirement: Accept modelscope provider
系统 SHALL 将 LLM provider 值 `modelscope`（规范化后）识别为魔搭 ModelScope，并使用 `modelscope_api_key` 与 `modelscope_base_url`（缺省国内 OpenAI 兼容推理地址）创建客户端。

#### Scenario: Provider modelscope with key
- **WHEN** 调用方或保底链使用 `provider=modelscope` 且 ModelScope API Key 已配置
- **THEN** 系统 SHALL NOT 因提供商名称拒绝，并 SHALL 使用魔搭 Base URL 发起调用

## MODIFIED Requirements

### Requirement: Unknown providers still rejected
系统对既非 `deepseek`、亦非智谱别名（`glm`/`zhipu`）、亦非 `siliconflow`、亦非 `modelscope` 的 provider SHALL 拒绝并报错。

#### Scenario: Unsupported provider
- **WHEN** 调用方传入 `provider` 为未知值（例如 `foo`）
- **THEN** 系统抛出表示不支持该提供商的错误

#### Scenario: Known free fallback providers accepted
- **WHEN** 调用方传入 `provider` 为 `siliconflow` 或 `modelscope` 且对应 API Key 已配置
- **THEN** 系统不因「未知提供商」拒绝该请求

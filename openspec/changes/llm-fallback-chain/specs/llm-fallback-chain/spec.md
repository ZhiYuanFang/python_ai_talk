## ADDED Requirements

### Requirement: Primary model then configured fallbacks on invoke
对 `llm_client.invoke`，当调用方传入首选 model 时，系统 SHALL 先使用该配置发起请求。当该次尝试因可恢复错误失败时，系统 MUST 按本地配置的保底列表顺序尝试后续 `(provider, name)`，跳过与已尝试项相同的项以及保底项 API Key 未配置的项。列表耗尽仍失败时，系统 MUST 向上抛出错误（不得静默返回空成功）。

#### Scenario: Primary succeeds
- **WHEN** 首选模型 invoke 成功
- **THEN** 系统不尝试保底列表中的后续模型
- **AND** 返回该次成功结果

#### Scenario: Primary 429 then fallback succeeds
- **WHEN** 首选模型返回可恢复失败（例如 HTTP 429）
- **AND** 保底列表中下一候选已配置有效 API Key 且调用成功
- **THEN** 系统使用该候选完成请求并对调用方返回成功结果
- **AND** 记录从首选切换到保底模型的告警或信息日志

#### Scenario: Empty or missing API key skips candidate
- **WHEN** 保底列表中某候选的提供商 API Key 为空
- **THEN** 系统跳过该候选并继续尝试后续候选（若有）

### Requirement: Fallback-only when model omitted on invoke
当 `invoke` 调用方未传入首选 model（`model_config` 为 None / 缺省）时，系统 SHALL 仅按 `LLM_FALLBACK_MODELS` 解析出的顺序尝试候选，不得隐式注入付费 deepseek 默认模型。若保底列表为空或均无可用 API Key，系统 MUST 抛出错误。

#### Scenario: No model uses fallback order only
- **WHEN** invoke 未带 model 且保底列表含多个已配置 key 的候选
- **THEN** 系统按保底列表顺序依次尝试
- **AND** 第一个成功的候选结果返回给调用方

#### Scenario: No model and empty usable fallbacks fails
- **WHEN** invoke 未带 model
- **AND** 保底列表为空或所有候选因缺少 API Key 被跳过
- **THEN** 系统抛出错误且不得假装调用成功

### Requirement: Stream does not use fallback chain
对 `llm_client.stream`，系统 MUST NOT 按 `LLM_FALLBACK_MODELS` 切换模型。系统 SHALL 仅使用调用方传入的唯一 model 发起流式请求；该次失败时 MUST 向上抛出，不得尝试保底列表中的其它模型。未传入可用 model 时，系统 MUST 抛出错误（不得回落保底列表）。

#### Scenario: Stream uses only request model
- **WHEN** stream 收到合法 model 配置
- **THEN** 系统仅使用该配置发起流式调用
- **AND** 即使该次因可恢复错误失败，也不尝试保底列表

#### Scenario: Stream without model fails
- **WHEN** stream 未收到可用 model 配置
- **THEN** 系统抛出错误
- **AND** 不读取或尝试 `LLM_FALLBACK_MODELS`

### Requirement: Recoverable errors only on invoke
系统 SHALL 仅在 `invoke` 的可恢复上游失败时切换保底模型，包括限流（429）、鉴权/禁用类（401/403，含 Model disabled）、服务端错误（5xx）、超时与连接失败，以及型号不可用（如 has no provider supported）。对明确的客户端请求非法（典型 400 内容/参数错误，且非型号可用性），系统 MUST NOT 为同一逻辑请求切换保底模型。

#### Scenario: Bad request content does not rotate
- **WHEN** 首选模型因请求内容/参数非法返回 400 类错误（非型号可用性文案）
- **THEN** 系统不尝试保底列表，并将该错误向上抛出

#### Scenario: Model unavailable rotates on invoke
- **WHEN** invoke 某候选因型号不可用失败（例如 Model disabled 或 has no provider supported）
- **AND** 仍有后续候选
- **THEN** 系统切换到下一候选继续尝试

### Requirement: Domestic permanent-free fallback catalog
默认保底列表 SHALL 仅包含国内、永久免费语义的提供商与模型（可含智谱 Flash、硅基流动、魔搭），MUST NOT 将付费 DeepSeek 或新人赠金型通道作为默认保底项。该列表仅用于 `invoke`。运维可通过环境变量覆盖列表与顺序。

#### Scenario: Default list excludes deepseek
- **WHEN** 使用仓库默认保底配置且未人为把 deepseek 写入保底环境变量
- **THEN** invoke 保底尝试序列中不包含 deepseek 提供商

#### Scenario: Default list may include glm
- **WHEN** 使用仓库默认保底配置
- **THEN** invoke 保底尝试序列可以包含 glm（智谱永久免费档）以便运维调序

### Requirement: Optional model on non-streaming HTTP contracts
intent 与 care_alert 分析请求的 `model` 字段 SHALL 为可选。省略时业务层 MUST 将空配置传入图/LLM，由 `llm_client.invoke` 走纯保底序。

#### Scenario: Care alert without model
- **WHEN** care_alert 分析请求未带 model
- **THEN** 请求校验通过
- **AND** 分析流程以无首选 model 调用 invoke

### Requirement: Required model on streaming HTTP contracts
clinic 与 tip 请求的 `model` 字段 SHALL 为必填。Go 在流式场景 MUST 传入完整 model；Python MUST NOT 在缺省 model 时对 clinic/tip 回落保底列表。

#### Scenario: Clinic without model rejected
- **WHEN** clinic 请求未带 model
- **THEN** 请求校验失败（或等价明确错误）
- **AND** 不发起依赖保底列表的 LLM stream

### Requirement: No VIP logic in Python
系统 MUST NOT 根据 VIP 或会员状态选择首选或保底模型；是否传入首选完全由调用方（Go）决定。

#### Scenario: Request model is always first on invoke when present
- **WHEN** invoke 调用方传入任意合法 model 配置
- **THEN** 系统将该配置作为候选序列的第一个尝试对象，无论业务侧是否 VIP

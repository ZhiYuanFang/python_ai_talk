## ADDED Requirements

### Requirement: Primary model then configured fallbacks
对 `llm_client.invoke` 与 `llm_client.stream`，系统 SHALL 先使用调用方传入的 model 配置发起请求。当该次尝试因可恢复错误失败时，系统 MUST 按本地配置的保底列表顺序尝试后续 `(provider, name)`，跳过与首选相同的项以及 API Key 未配置的项。列表耗尽仍失败时，系统 MUST 向上抛出错误（不得静默返回空成功）。

#### Scenario: Primary succeeds
- **WHEN** 首选模型调用成功
- **THEN** 系统不尝试保底列表中的后续模型
- **AND** 返回该次成功结果（invoke 全文或 stream 增量）

#### Scenario: Primary 429 then fallback succeeds
- **WHEN** 首选模型返回可恢复失败（例如 HTTP 429）
- **AND** 保底列表中下一候选已配置有效 API Key 且调用成功
- **THEN** 系统使用该候选完成请求并对调用方返回成功结果
- **AND** 记录从首选切换到保底模型的告警或信息日志

#### Scenario: Empty or missing API key skips candidate
- **WHEN** 保底列表中某候选的提供商 API Key 为空
- **THEN** 系统跳过该候选并继续尝试后续候选（若有）

### Requirement: Recoverable errors only
系统 SHALL 仅在可恢复的上游失败时切换保底模型，包括限流（429）、服务端错误（5xx）、超时与连接失败。对明确的客户端请求非法（典型 400 内容/参数错误），系统 MUST NOT 为同一逻辑请求切换保底模型。

#### Scenario: Bad request does not rotate
- **WHEN** 首选模型因请求非法返回 400 类错误
- **THEN** 系统不尝试保底列表，并将该错误向上抛出

### Requirement: Domestic permanent-free fallback catalog
默认保底列表 SHALL 仅包含国内、永久免费语义的提供商与模型（限速或日次重置均可），MUST NOT 将付费 DeepSeek 或新人赠金型通道作为默认保底项。运维可通过环境变量覆盖列表；未配置列表时行为为仅使用首选模型。

#### Scenario: Default list excludes deepseek
- **WHEN** 使用仓库默认保底配置且未人为把 deepseek 写入保底环境变量
- **THEN** 保底尝试序列中不包含 deepseek 提供商

### Requirement: Stream fallback only before first yield
对 `stream`，系统 SHALL 仅在尚未向调用方产出任何非空 content/thinking 增量之前，因可恢复失败切换保底并重开流。若已向调用方 yield 过非空增量后失败，系统 MUST NOT 静默更换模型继续推流。

#### Scenario: Failure before first token retries next model
- **WHEN** stream 在首包产出前因可恢复错误失败
- **AND** 下一保底候选可用
- **THEN** 系统用下一候选重新发起 stream

#### Scenario: Failure after tokens does not swap model
- **WHEN** stream 已向调用方 yield 过非空增量后上游失败
- **THEN** 系统不切换保底模型继续同一响应流，并按失败路径结束或上抛

### Requirement: No VIP logic in Python
系统 MUST NOT 根据 VIP 或会员状态选择首选或保底模型；首选完全由调用方传入的 model 决定。

#### Scenario: Request model is always first
- **WHEN** 调用方传入任意合法 model 配置
- **THEN** 系统将该配置作为保底链的第一个尝试对象，无论业务侧是否 VIP

## REMOVED Requirements

### Requirement: Primary model then configured fallbacks on invoke
**Reason**: 跨模型保底串行尝试导致超时、收益低；选型改由调用方唯一指定。
**Migration**: `invoke` 仅使用请求传入的唯一 model；失败立即上抛，由业务层给出「脑电波过载，请稍后重试」。

### Requirement: Fallback-only when model omitted on invoke
**Reason**: 禁止 Python 在无 model 时用保底列表充当默认选型。
**Migration**: 省略 model 时直接失败；Go 必须传入可用 model。

### Requirement: Recoverable errors only on invoke
**Reason**: 不再存在「可恢复则换下一候选」的行为。
**Migration**: 任意上游失败均结束本次 invoke（可保留日志）；不切换其它 provider/name。

### Requirement: Domestic permanent-free fallback catalog
**Reason**: 保底目录不再使用。
**Migration**: 删除 `LLM_FALLBACK_MODELS` / `llm_fallback_models` 配置；provider 接入可保留供 Go 选型。

### Requirement: Optional model on non-streaming HTTP contracts
**Reason**: intent / care_alert 不再允许省略 model 走保底。
**Migration**: 与 clinic/tip 一样由 Go 传入完整 model；缺省则校验失败或业务失败文案。

## ADDED Requirements

### Requirement: Invoke uses only request model
对 `llm_client.invoke`，系统 SHALL 仅使用调用方传入的唯一合法 `model`（含 provider 与 name）发起一次请求。系统 MUST NOT 按保底列表或其它本地目录切换到不同的 `(provider, name)`。该次失败时 MUST 将错误向上抛出（不得静默当作成功）。未传入可用 model 时，系统 MUST 抛出错误，MUST NOT 使用默认单模或保底列表。

#### Scenario: Invoke with model succeeds
- **WHEN** invoke 收到合法 model 且上游成功
- **THEN** 系统返回该次结果
- **AND** SHALL NOT 尝试任何其它模型

#### Scenario: Invoke with model fails once
- **WHEN** invoke 收到合法 model 且该次上游失败（含 429/5xx/超时）
- **THEN** 系统将该错误向上抛出
- **AND** SHALL NOT 切换到其它 provider 或 name

#### Scenario: Invoke without model fails
- **WHEN** invoke 未收到可用 model（None 或 provider/name 为空）
- **THEN** 系统抛出错误
- **AND** SHALL NOT 读取或尝试 `LLM_FALLBACK_MODELS` 或等价保底配置

### Requirement: Stream does not use fallback chain
对 `llm_client.stream`，系统 MUST NOT 按保底列表切换模型。系统 SHALL 仅使用调用方传入的唯一 model 发起流式请求；该次失败时 MUST 向上抛出。未传入可用 model 时，系统 MUST 抛出错误。

#### Scenario: Stream uses only request model
- **WHEN** stream 收到合法 model 配置
- **THEN** 系统仅使用该配置发起流式调用
- **AND** 即使该次因可恢复错误失败，也不尝试其它模型

#### Scenario: Stream without model fails
- **WHEN** stream 未收到可用 model 配置
- **THEN** 系统抛出错误
- **AND** 不读取保底列表

### Requirement: Required model on LLM HTTP contracts
intent、care_alert、clinic 与 tip 等会调用 LLM 的请求，其 `model` 字段 SHALL 由调用方（Go）提供可用配置。Python MUST NOT 在缺省 model 时回落保底列表或注入默认单模。缺省时 MUST 以校验失败或等价明确错误结束（用户可见路径须导向过载重试文案，见意图图相关要求）。

#### Scenario: Intent without model fails clearly
- **WHEN** intent 分析请求未带可用 model
- **THEN** 系统不以保底列表完成分类
- **AND** SHALL 失败或返回明确不可用结果（不得假装分类成功）

#### Scenario: Care alert without model fails clearly
- **WHEN** care_alert 分析请求未带可用 model
- **THEN** 系统不以保底列表完成分析
- **AND** SHALL 失败或返回明确错误

### Requirement: No VIP logic in Python
系统 MUST NOT 根据 VIP 或会员状态选择模型；是否传入何种 model 完全由调用方（Go）决定。Python MUST NOT 实现 VIP 分支选模。

#### Scenario: Request model is the only model used
- **WHEN** 调用方传入任意合法 model 配置
- **THEN** 系统仅使用该配置发起 LLM 调用
- **AND** 不因业务侧是否 VIP 而改换模型

### Requirement: Non-model retries may remain
系统 MAY 保留与换模无关的等待或重试（例如 Redis 并发闸门获取许可时的等待、兄弟仓 HTTP 客户端重试、业务节点在 LLM 失败时使用默认数据结构）。系统 MUST NOT 将「更换 LLM provider/name」实现为重试策略。系统 MUST NOT 在本变更中新增「同一 model 自动再调用 N 次」的 LLM 重试环（除非另行变更明确要求）。

#### Scenario: Gate wait is not model rotation
- **WHEN** Redis 并发闸门暂时无法获取许可并在超时前等待重试
- **THEN** 系统仍针对同一 model 获取许可
- **AND** SHALL NOT 因此切换到其它 LLM 模型

## MODIFIED Requirements

### Requirement: Required model on streaming HTTP contracts
clinic 与 tip 请求的 `model` 字段 SHALL 为必填。Go MUST 传入完整 model；Python MUST NOT 在缺省 model 时回落保底列表。本要求与「Required model on LLM HTTP contracts」一致，stream 路径行为不变。

#### Scenario: Clinic without model rejected
- **WHEN** clinic 请求未带 model
- **THEN** 请求校验失败（或等价明确错误）
- **AND** 不发起依赖保底列表的 LLM stream

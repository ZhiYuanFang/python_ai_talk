## MODIFIED Requirements

### Requirement: Required model on streaming HTTP contracts

clinic 等流式/同步陪伴请求的 `model` 字段 SHALL 为**可选**。Go MAY 省略 `model`。缺省时 Python MUST 接受请求，MUST NOT 因缺 `model` 校验失败；实际上游选型 SHALL 遵循临时 runtime（见 `llm-runtime-model-override`）。系统 MUST NOT 在缺省时回落保底换模列表。本要求与「Required model on LLM HTTP contracts」一致。

#### Scenario: Clinic without model accepted

- **WHEN** clinic 请求未带 model
- **THEN** 请求校验 MUST 通过
- **AND** MUST NOT 发起依赖保底列表的 LLM 换模；上游 SHALL 使用临时 runtime

#### Scenario: Clinic with model still accepted

- **WHEN** clinic 请求带合法 model
- **THEN** 请求校验 MUST 通过
- **AND** 该 model 可写入 state/日志，但对临时阶段实际上游选型无约束力

### Requirement: Required model on LLM HTTP contracts

intent、care_alert、clinic 与 growth_trajectory 等会调用 LLM 的请求，其 `model` 字段 SHALL 为可选。调用方（Go）MAY 省略。Python MUST NOT 在缺省 model 时回落保底换模列表。缺省时 MUST 接受入站并进入既有业务路径，由 `llm_client` 临时 runtime 完成实际上游选型。有传入时 MAY 写入 state/日志。

#### Scenario: Intent without model proceeds

- **WHEN** intent 分析请求未带 model
- **THEN** 系统 MUST NOT 以 `Field required` / 等价校验失败拒绝
- **AND** MUST NOT 使用保底换模列表完成分类；上游 SHALL 使用临时 runtime

#### Scenario: Care alert without model proceeds

- **WHEN** care_alert 分析请求未带 model
- **THEN** 系统 MUST NOT 因缺 model 校验失败
- **AND** MUST NOT 使用保底换模列表；上游 SHALL 使用临时 runtime

## ADDED Requirements

### Requirement: Downstream model resolve tolerates omission

当请求 `model` 为省略或 null 时，路由与 `resolve_model_config`（及等价解析）MUST NOT 抛出「model 必传」类错误；MUST 产出可供图使用的空/占位配置，交由 `llm_client` 临时 runtime。系统 MUST NOT 因此恢复跨 provider/name 的保底换模链。

#### Scenario: resolve_model_config None does not raise required

- **WHEN** `resolve_model_config(None)`（或路由在 `request.model is None` 时构建 llm_model）
- **THEN** MUST NOT 抛出「必传」校验错误
- **AND** 后续 LLM 调用仍 SHALL 走临时 runtime

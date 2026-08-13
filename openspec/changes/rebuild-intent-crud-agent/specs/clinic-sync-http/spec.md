## ADDED Requirements

### Requirement: 非流式陪伴接口
系统 SHALL 提供 `POST /v1/clinic` HTTP 接口，接收与 `/v1/clinic/stream` 相同的 `ClinicRequest`（`question`、`device_no`、`model`），同步返回陪伴回答。响应 MUST 为陪伴外壳（至少包含非空 `answer` 文本，以及可用于反馈的 `answer_id` 若该次生成有 id），MUST NOT 使用 `IntentResponse` 的 `target_type`/`action`/`events` 作为主契约。该接口 SHALL 使用与 stream 相同的 `clinic_graph` 数据准备与生成能力（`ainvoke` 或等价同步路径），SHALL NOT 调用 `intent_graph`。

#### Scenario: 同步成功返回 answer
- **WHEN** 客户端 POST `/v1/clinic`，body 含有效 `question` 与 `device_no` 及 `model`
- **THEN** 服务返回 HTTP 200
- **AND** JSON 含非空 `answer`（或约定兜底文案）
- **AND** 响应 MUST NOT 把 `target_type` 设为 `feeding`

#### Scenario: 与 stream 共用 clinic 图
- **WHEN** 非流式 `/v1/clinic` 执行
- **THEN** 系统 SHALL 走 `clinic_graph`（含会话、可选历史与生成）
- **AND** SHALL NOT 执行喂养向量匹配或 history add

#### Scenario: 缺少必要参数
- **WHEN** body 缺少 `question` 或 `device_no`
- **THEN** 服务 SHALL 返回 4xx 校验错误

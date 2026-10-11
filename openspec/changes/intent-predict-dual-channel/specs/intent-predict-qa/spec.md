## ADDED Requirements

### Requirement: Intent SHALL support target_type predict with separate channel and time_answer

The feeding intent pipeline SHALL accept `target_type` value `predict`. When `target_type` is `predict`, the result MUST include `predict_channel` of `active` or `next` and `time_answer` of `clock` or `remain` as **separate** fields (MUST NOT collapse them into a single combined enum for classification storage). When `target_type` is not `predict`, `predict_channel` and `time_answer` MUST be empty or omitted. Predict turns MUST NOT use `history_mode` point/daily speak-history last-record templates as the primary answer path.

意图 MUST 支持 `target_type=predict`，且 `predict_channel` 与 `time_answer` 分维存储；非 predict 不得携带有效预测维；predict MUST NOT 以查史上一次用时为主答。

#### Scenario: Wake-soon classified as predict active remain

- **WHEN** 用户语义为询问进行中睡眠还需多久醒来（如「大概还有多久醒来」）且 TYPE 飞轮或 TYPE LLM 采用结果
- **THEN** `target_type` MUST 为 `predict`，`predict_channel` MUST 为 `active`，`time_answer` MUST 为 `remain`

#### Scenario: Next sleep classified as predict next remain

- **WHEN** 用户语义为询问距离下次睡觉还有多久（如「还有多久睡觉」）且 TYPE 飞轮或 TYPE LLM 采用结果
- **THEN** `target_type` MUST 为 `predict`，`predict_channel` MUST 为 `next`，`time_answer` MUST 为 `remain`

### Requirement: Predict dimensions SHALL be resolved via TYPE LLM or type-cue flywheel

Classification of `predict` / `predict_channel` / `time_answer` SHALL be produced by the TYPE keyword flywheel hit or the TYPE small LLM (including `need_confirm` and `keywords` per existing TYPE flywheel rules). The system MUST NOT use local keyword/regex tables as the primary authority to map utterances to `predict_channel` or `time_answer`, or to force「多久」into `history` when the adopted TYPE result is `predict`.

预测维 MUST 由类型飞轮或 TYPE LLM 判定；MUST NOT 以本地词表作为 channel/time_answer 或「多久→history」的主权威（在已采用 predict 时）。

#### Scenario: Flywheel hit skips TYPE LLM

- **WHEN** 段原文命中 `feeding_type_cues` 且 payload 含合法 predict 与两维
- **THEN** 系统 MUST 采用该 payload，且 MUST NOT 仅为判定这两维再跑 TYPE LLM

#### Scenario: Cold path LLM emits both dimensions

- **WHEN** 类型飞轮未命中且走 TYPE LLM
- **THEN** 模型输出 MUST 可携带 `predict_channel` 与 `time_answer`；采用 `predict` 后写入飞轮的 keywords 载荷 MUST 含这两维

### Requirement: speak_predict SHALL answer from Go predict stores by channel

When `target_type` is `predict`, the intent graph SHALL route to a predict speak path (not `speak_history` as primary). For `predict_channel=active` the service MUST load active ETAs via the existing voice internal active-eta GET and match the spoken event. For `predict_channel=next` the service MUST load imminent pending via voice internal GET `GET /voice/internal/api/predict/imminent/pending?deviceNo=` (twin Go) and match by event id (including catalog root as applicable). Matching failure, empty list, or GET failure MUST yield a Chinese uncertainty message and MUST NOT answer with last-completed history duration copy such as「上一次…用时…」solely due to missing predict data.

predict MUST 走预测播报：active 用 active-eta，next 用 imminent internal GET；失败/无匹配 MUST 估不准且 MUST NOT 因此念上一次用时。

#### Scenario: Active remain before deadline

- **WHEN** `predict_channel=active`、`time_answer=remain`、匹配到 `expectEndAt` 且当前时间未晚于该锚点
- **THEN** 对用户文案 MUST 表达剩余时长语义（相对时间）

#### Scenario: Remain overdue copy

- **WHEN** `time_answer=remain` 且当前时间严格晚于所用锚点（`expectEndAt` 或 `nextAt`）
- **THEN** 文案 MUST 含「已经过了预计时间」

#### Scenario: Clock answer

- **WHEN** `time_answer=clock` 且锚点有效
- **THEN** 文案 MUST 含「预计约」与墙钟时刻语义（HH:mm）

#### Scenario: No predict data no history fallback

- **WHEN** 对应 channel 的 GET 失败或无匹配项
- **THEN** 播报 MUST 仍可完成，MUST 表达暂时估不准类语义，且 MUST NOT 仅因缺失预测数据而输出「上一次」加「用时」类查史完成句

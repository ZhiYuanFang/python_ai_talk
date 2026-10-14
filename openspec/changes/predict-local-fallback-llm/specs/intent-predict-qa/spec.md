## MODIFIED Requirements

### Requirement: speak_predict SHALL answer from Go predict stores by channel

When `target_type` is `predict` (or read with `read_source=predict`), the intent graph SHALL route to a predict speak path (not `speak_history` as primary). For `predict_channel=active` the service MUST load active ETAs via the existing voice internal active-eta GET and match the spoken event. For `predict_channel=next` the service MUST load imminent pending via voice internal GET `GET /voice/internal/api/predict/imminent/pending?deviceNo=` (twin Go) and match by event id (including catalog root as applicable). When a matching Go anchor exists, the service MUST keep template clock/remain speak behavior (including remain overdue copy「已经过了预计时间」). When Go GET fails, the list is empty, or no match exists (or the event is an appointment root that is not answered from Go predict Redis), the service MUST enter the local algorithm / appointment cold path defined by `intent-predict-algo-fallback` and MUST NOT answer with last-completed history duration copy such as「上一次…用时…」solely due to missing Go predict data. The cold path MUST NOT be skipped in favor of only an uncertainty template when algorithm or appointment fallback is available.

predict MUST 走预测播报：active 用 active-eta，next 用 imminent；Go 命中保留模板；Go 无匹配或预约等须进本地/约定兜底，且 MUST NOT 因此念上一次用时。

#### Scenario: Active remain before deadline

- **WHEN** `predict_channel=active`、`time_answer=remain`、匹配到 `expectEndAt` 且当前时间未晚于该锚点
- **THEN** 对用户文案 MUST 表达剩余时长语义（相对时间）

#### Scenario: Remain overdue copy

- **WHEN** `time_answer=remain` 且当前时间严格晚于所用锚点（`expectEndAt` 或 `nextAt`）且走 Go 模板路径
- **THEN** 文案 MUST 含「已经过了预计时间」

#### Scenario: Clock answer

- **WHEN** `time_answer=clock` 且 Go 锚点有效
- **THEN** 文案 MUST 含「预计约」与墙钟时刻语义（HH:mm）

#### Scenario: Go miss enters algorithm fallback

- **WHEN** 对应 channel 的 GET 失败或无匹配项且事件非仅依赖预约约定失败
- **THEN** 系统 MUST 进入本地算法（及语境史 + LLM）兜底路径
- **AND** MUST NOT 仅因缺失 Go 预测数据而输出「上一次」加「用时」类查史完成句
- **AND** MUST NOT 在仍可跑算法兜底时仅以「暂时估不准」结束（样本不足等算法降级除外）

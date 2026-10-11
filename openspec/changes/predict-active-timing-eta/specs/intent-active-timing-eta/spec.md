## ADDED Requirements

### Requirement: Intent speak_history SHALL enrich in-progress-only answers with ETA

When the feeding intent `speak_history` path answers with the in-progress-only template (no completed row selected), the service SHALL attempt to load active ETAs for the device from the Go voice internal GET  
`GET /voice/internal/api/predict/active-eta?deviceNo=`  
(authenticated with the shared device-gateway internal secret header). On a successful match to the spoken history row (`historyId` from history row `id`, else `leafEventId`, else `rootEventId` via catalog), the spoken content MUST append estimated-end copy aligned with the App: wall-clock「预计约 HH:mm 结束」, and when now is strictly after `expectEndAt` (unix seconds) MUST append「 · 已超时». When GET fails, the list is empty, or no match exists, the service MUST keep the existing in-progress wording and MUST NOT fail the intent turn solely for missing ETA.

点查仅进行中时 MUST 经 voice internal GET 拉 ETA 并按 historyId→leaf→root 匹配，拼接「预计约 HH:mm 结束」；超时 MUST 含「 · 已超时」；失败或无匹配 MUST 降级为原话术且不得因此失败整轮意图。

#### Scenario: Matched ETA appended

- **WHEN** 仅进行中播报且 GET 返回匹配 leaf 的 expectEndAt（未超时）
- **THEN** 对用户文案 MUST 含「预计约」与结束时刻语义（形如「预计约 HH:mm 结束」）

#### Scenario: Overdue marker

- **WHEN** 匹配 ETA 且当前时间严格晚于 expectEndAt
- **THEN** 文案 MUST 含「 · 已超时」（或等价含「已超时」且与预计结束同句）

#### Scenario: Degrade on GET failure

- **WHEN** internal GET 失败（含鉴权失败、网络错误）
- **THEN** 播报 MUST 仍可完成，且 MUST NOT 仅因 ETA 缺失而返回错误意图结果

#### Scenario: Match by historyId then leaf

- **WHEN** ETA 项带 historyId 且与当前播报历史行 id 一致
- **THEN** MUST 使用该条 expectEndAt（优先于仅 leaf/root 匹配）

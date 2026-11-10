## ADDED Requirements

### Requirement: Predict next channel SHALL match by eventId and MAY reverse-match parentEventName

When `predict_channel=next`, the service MUST load imminent pending from Go and match the spoken event primarily by `eventId` (including catalog leaf/root resolution as today). When no `eventId` match exists, and the spoken/catalog root event has a non-empty authoritative `name`, the service MUST attempt to match pending items whose optional `parentEventName` equals that name after trim. The service MUST accept items that omit `parentEventName` (legacy). The service MUST NOT require or prefer `expectLeafTitle` for naming or matching; display/speak name MUST come from `title` or catalog. next 通道 MUST 以 eventId 优先匹配；未命中时 MUST 可用 parentEventName 按根名反推；MUST NOT 依赖 expectLeafTitle。

#### Scenario: Child pending matched by eventId without leafTitle

- **WHEN** pending 项为子 eventId、含 title、可选 parentEventName、无 expectLeafTitle，且用户所指事件 id 与该子 eventId 对齐
- **THEN** 服务 MUST 能按子 eventId 匹配并播报，MUST NOT 因缺 leafTitle 失败

#### Scenario: Root name reverse-matches child pending via parentEventName

- **WHEN** 用户话语解析到根事件（或根权威名），pending 中无该根 eventId 项，但存在子项且其 `parentEventName` 与根权威名 trim 后相等
- **THEN** 服务 MUST 命中该子项（多条时按既有 nextAt 择优）并播报，MUST NOT 因仅有子 eventId 而判未命中

#### Scenario: Legacy root item without parentEventName

- **WHEN** pending 项无 parentEventName（旧客户端）
- **THEN** 服务 MUST 仍按 eventId 匹配，行为与今日根级兼容

### Requirement: Predict active channel SHALL tolerate missing expectEndAt and MUST NOT use parentEventName

When `predict_channel=active`, the service MUST load active-eta from Go and match by event identity as today (leaf/root/`eventId`). The service MUST NOT use `parentEventName` on active-eta (Go does not project it). When `expectEndAt` is omitted, null, or non-positive (including `0`), the service MUST still treat a otherwise-matched item as in-progress for speak purposes and MUST NOT invent an end clock time. active 通道 MUST 容忍无结束时间且 MUST NOT 编造结束钟点；MUST NOT 读 parentEventName。

#### Scenario: Active without end

- **WHEN** active-eta 项已按事件身份命中，且有 start、无正 expectEndAt（省略/null/0）
- **THEN** 服务 MUST 可播进行中语义，MUST NOT 输出具体预计结束时刻

#### Scenario: Legacy positive end still speaks end

- **WHEN** active-eta 项已命中且含正 expectEndAt
- **THEN** 服务 MUST 按既有 clock/remain 模板播报预计结束相关语义

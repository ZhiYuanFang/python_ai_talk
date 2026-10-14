## ADDED Requirements

### Requirement: Predict cold path SHALL use fixed seven-day history for local algorithm

When the predict speak path cannot answer from Go active-eta or imminent anchors, for a non-appointment event the system SHALL load approximately the last seven Shanghai calendar days of history (aligned with Flutter prediction range) and run a local prediction tool whose outputs MAY include median interval, nextAt, expected duration, and expected amount. The algorithm window MUST NOT be driven by the user utterance TIME resolution. User TIME MUST NOT change the seven-day algorithm bounds.

#### Scenario: Algorithm ignores utterance day words

- **WHEN** 用户问「这两天大概隔多久喂一次」且进入算法兜底且事件非预约
- **THEN** 系统 SHALL 以近 7 日史为算法输入
- **AND** MUST NOT 仅用「这两天」物化窗作为算法拉史上界

### Requirement: Predict cold path SHALL inject context history only when utterance needs it

On the cold path, the system MUST NOT always fetch context history for the LLM. When the utterance is a pure next-when / remain-style question without day-word, near-term, or pattern/comparative cues, the answering LLM MUST receive the original utterance and tool/appointment JSON only (compact history omitted). When the utterance includes such cues (day words, 最近/这两天, 隔多久/规律/比上次, or equivalent), the system SHALL resolve a context time window using the same TIME methods as read-record, fetch history for that window, and format it with the shared `build_feeding_history_prompt_blocks`. When a context fetch is triggered but the utterance has no sharper window, the context history window MAY default to the same seven-day range as the algorithm. Algorithm seven-day bounds MUST remain independent of this gate.

#### Scenario: Pure next-when skips context history

- **WHEN** 用户问「下一次配方奶是什么时候」类且进入算法兜底且工具样本足够
- **THEN** 系统 MUST NOT 仅为该问再拉语境史注入 LLM
- **AND** SHALL 以原话 + 工具 JSON 调用 LLM（或等价终答）
- **AND** 算法轨仍 MUST 使用固定近 7 日（非预约）

#### Scenario: Context window feeds LLM not algorithm

- **WHEN** 用户原话含可解析相对时间或规律/近况线索且进入预测兜底
- **THEN** 系统 SHALL 用与查史相同的 TIME 路径得到语境窗并拉史
- **AND** SHALL 以共享紧凑史拼法注入 LLM 提示
- **AND** 算法轨仍 MUST 使用固定近 7 日（非预约）

### Requirement: Cold-path final answer SHALL be LLM grounded on tools and optional history

When algorithm or appointment outputs are sufficient, the cold-path user-facing answer MUST be produced by an LLM call that receives the original utterance, the tool/appointment JSON, and compact context history only when the context-history gate above requires it. The system prompt MUST require Chinese reasoning and MUST forbid inventing numeric predictions not present in the injected tool or (when present) history evidence. On intent SSE paths the LLM call MUST use `stream(thinking_enabled=True)`.

#### Scenario: Grounded interval answer

- **WHEN** 工具给出合法 interval/nextAt 且样本足够
- **THEN** 终答 MUST 经 LLM 结合原话与注入块生成
- **AND** MUST NOT 在无工具/史证据时编造具体间隔分钟数

### Requirement: Insufficient samples or missing appointment MUST degrade without inventing

For non-appointment events, when the local tool lacks sufficient samples (aligned with Flutter minimum sample rules), the system MUST return a Chinese message that data is too little to predict and MUST NOT call the answering LLM solely to invent numbers. For appointment roots, when nextAt is missing or unusable, the system MUST return a clear no-appointment-time style message and MUST NOT fabricate nextAt via interval algorithm.

#### Scenario: Too few samples

- **WHEN** 近 7 日有效间隔样本不足算法门槛
- **THEN** 系统 MUST 直接表达数据量太少无法预测
- **AND** MUST NOT 为此编造间隔或 nextAt

#### Scenario: Appointment without nextAt

- **WHEN** 命中事件 `isAppointment=true` 且约定 nextAt 无效（如 0）
- **THEN** 系统 MUST 明确无下次约定类语义
- **AND** MUST NOT 用喂养间隔算法冒充预约时间

### Requirement: Appointment events SHALL bypass interval algorithm by event field

When the spoken/matched catalog event itself is marked appointment (`isAppointment` / Go `event.is_appointment` = 1), the cold path MUST obtain nextAt from the device appointment-next API with that **same eventId** (twin internal GET aligned with App appointment/next) and MUST NOT compute nextAt from seven-day interval medians. The system MUST NOT treat a non-appointment event as appointment merely because its catalog root or a sibling under the same root is marked appointment. Appointment results MAY be included in the device algorithm snapshot cache keyed by that eventId.

#### Scenario: Vaccine next time uses appointment nextAt

- **WHEN** 用户询问预约类事件下次时间且该事件 `isAppointment=true`
- **THEN** 系统 SHALL 使用 appointment nextAt（eventId=该事件）作为工具侧锚点
- **AND** MUST NOT 仅用近 7 日历史间隔推算该预约 nextAt

#### Scenario: Non-appointment leaf under shared root uses interval path

- **WHEN** 用户询问日常事件（如配方奶）且该事件 `isAppointment=false`，即使同根下另有预约叶
- **THEN** 系统 MUST NOT 走预约约定降级文案
- **AND** SHALL 按非预约冷路径（Go miss 后近 7 日算法 ± LLM）处理

### Requirement: Algorithm snapshot SHALL use Redis with TTL and CUD invalidation

The system SHALL cache per-device local algorithm (and appointment) tool snapshots in Redis with TTL of 10 minutes. On successful create/update/delete (and history-mutating end) persistence for that device, the system MUST delete the device snapshot key. Snapshot hits MUST skip re-fetching seven-day history for recomputation and MUST skip re-running the interval tool, but MUST NOT skip the answering LLM when a cold-path LLM answer is required. The snapshot MUST NOT be written into intent or TIME classification flywheels.

#### Scenario: Repeat predict reuses snapshot

- **WHEN** 同一 device 在 TTL 内连续进入算法兜底且无 CUD 落库
- **THEN** 系统 SHALL 可复用 Redis 快照中的工具数字
- **AND** MUST NOT 仅为重复问题再次拉取近 7 日并重算间隔

#### Scenario: CUD clears snapshot

- **WHEN** 该 device 意图 create/update/delete（或改史 end）落库成功
- **THEN** 系统 MUST 删除该 device 的预测算法 Redis 快照
